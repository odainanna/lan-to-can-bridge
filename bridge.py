import logging
from threading import Thread

import can
from can.interfaces.pcan.pcan import PcanBus

from lan_bus import LANBus
from lan_utils import FromCanTypeEnum, MarkerEnum

# setup logging
logging.basicConfig(level=logging.ERROR)


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


class Bridge:
    def __init__(self, net, port, seg, bitrate, interface):
        if not can.detect_available_configs(interface):
            raise ValueError('No available configs')
        self._net = net
        self._port = port
        self._seg = seg
        self._bitrate = bitrate
        self._interface = interface

        self._can_1 = can.Bus(interface=interface, channel='PCAN_USBBUS1', bitrate=bitrate)
        self._can_2 = can.Bus(interface=interface, channel='PCAN_USBBUS2', bitrate=bitrate)
        self._lan_bus = LANBus(port=port, dest='239.0.0.' + str(seg), segment=seg)

        self.counter = {self._can_1: 0, self._can_2: 0, self._lan_bus: 0}

    def fwd_to_lan(self, can_bus):
        logging.info(f'listening to {can_bus}')
        while True:
            msg: can.Message = can_bus.recv()
            if msg.error_state_indicator or msg.is_error_frame:
                continue
            last_digit_of_channel_name = int(can_bus.channel_info[-1])
            self._lan_bus.send(msg, marker=last_digit_of_channel_name)
            self.counter[self._lan_bus] += 1  # counter += 1
            logging.info(f'{self._lan_bus} sent {msg}')

    def _send(self, can_bus, msg: can.Message):
        try:
            can_bus.send(msg)
            logging.info(f'{can_bus} sent {msg}')
            self.counter[can_bus] += 1  # counter += 1  todo: multiple messages in one?
            return True
        except can.interfaces.pcan.pcan.PcanCanOperationError as e:
            logging.warning(e)
            return False

    def reset_bus(self, bus):
        bus.shutdown()
        return can.Bus(interface=self._interface, channel=bus.channel_info, bitrate=self._bitrate)

    def fwd_to_can(self):
        logging.info(f'listening to {self._lan_bus}')
        while True:
            lan_msg_obj = self._lan_bus.recv()
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
                    reset_bus_1 = not self._send(self._can_1, can_message)
                if lan_msg.marker == MarkerEnum.CAN_2.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    reset_bus_2 = not self._send(self._can_2, can_message)

            # if sending caused an error on a bus, try to reset the bus
            if reset_bus_1:
                self._can_1 = self.reset_bus(self._can_1)
                logging.warning(f'Reset {self._can_1}')
            if reset_bus_2:
                self._can_2 = self.reset_bus(self._can_2)
                logging.warning(f'Reset {self._can_2}')

    def report(self):
        return self.counter

    def start(self):
        Thread(target=self.fwd_to_lan, args=(self._can_1,), daemon=True).start()
        Thread(target=self.fwd_to_lan, args=(self._can_2,), daemon=True).start()
        Thread(target=self.fwd_to_can, daemon=True).start()
