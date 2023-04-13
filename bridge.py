# pip install python-can msgpack uptime
import argparse
import logging
import sys
from threading import Thread

import can
from can.interfaces.pcan.pcan import PcanBus

from lan_bus import LANBus
from lan_utils import FromCanTypeEnum, MarkerEnum

# parse args
parser = argparse.ArgumentParser()
parser.add_argument('--net', default='127.0.0.1')
parser.add_argument('--port', default=62222, type=int)
parser.add_argument('--seg', default=5, type=int)
parser.add_argument('--bitrate', default=125000, type=int)
parser.add_argument('--interface', default='pcan')
args = parser.parse_args()

# setup logging
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    if not can.detect_available_configs(args.interface):
        logging.debug('No available configs.')
        sys.exit()

    CAN_1 = can.Bus(interface=args.interface, channel='PCAN_USBBUS1', bitrate=args.bitrate)
    CAN_2 = can.Bus(interface=args.interface, channel='PCAN_USBBUS2', bitrate=args.bitrate)
    LAN_BUS = LANBus(port=args.port, dest='239.0.0.' + str(args.seg), segment=args.seg)


    def fwd_to_lan(can_bus):
        logging.info(f'listening to {can_bus}')
        while True:
            msg: can.Message = can_bus.recv()
            if msg.error_state_indicator or msg.is_error_frame:
                continue
            last_digit_of_channel_name = int(can_bus.channel_info[-1])
            LAN_BUS.send(msg, marker=last_digit_of_channel_name)
            logging.info(f'{LAN_BUS} sent {msg}')


    def create_can_msg(lan_msg):
        return can.Message(
            timestamp=lan_msg.sec1970,
            arbitration_id=lan_msg.arbitration_id,
            is_extended_id=False,  # 11 bit
            is_remote_frame=False,
            is_error_frame=False,
            channel=None,
            dlc=lan_msg.dlc,
            data=lan_msg.data[: lan_msg.dlc],
            check=True,
        )


    def _send(can_bus: can.Bus, msg: can.Message):
        try:
            can_bus.send(msg)
            logging.info(f'{can_bus} sent {msg}')
            return True
        except can.interfaces.pcan.pcan.PcanCanOperationError as e:
            logging.warning(e)
            return False


    def reset_bus(bus: can.Bus):
        bus.shutdown()
        return can.Bus(interface=args.interface, channel=bus.channel_info, bitrate=args.bitrate)


    def fwd_to_can():
        global CAN_1, CAN_2
        logging.info(f'listening to {LAN_BUS}')
        while True:
            lan_msg_obj = LAN_BUS.recv()
            # if a lan message is marked "from can", assume it has been forwarded already and do not
            # forward
            message_has_been_forwarded_already = lan_msg_obj.header.from_can_type == FromCanTypeEnum.CAN
            if message_has_been_forwarded_already:
                continue

            # try to send all messages
            reset_bus_1, reset_bus_2 = False, False
            for lan_msg in lan_msg_obj.messages:
                can_message = create_can_msg(lan_msg)
                if lan_msg.marker == MarkerEnum.CAN_1.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    reset_bus_1 = not _send(CAN_1, can_message)
                if lan_msg.marker == MarkerEnum.CAN_2.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    reset_bus_2 = not _send(CAN_1, can_message)

            # if sending caused an error on a bus, try to reset the bus
            if reset_bus_1:
                CAN_1 = reset_bus(CAN_1)
                logging.warning(f'Reset {CAN_1}')
            if reset_bus_2:
                CAN_2 = reset_bus(CAN_2)
                logging.warning(f'Reset {CAN_2}')


    def bridge():
        Thread(target=fwd_to_lan, args=(CAN_1,), daemon=True).start()
        Thread(target=fwd_to_lan, args=(CAN_2,), daemon=True).start()
        Thread(target=fwd_to_can, daemon=True).start()
        input('Press enter to exit\n')


    logging.info('bridging...')
    bridge()
