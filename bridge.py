# pip install pythoncan msgpack uptime
import argparse
from datetime import datetime
from threading import Thread

import can
from can.interfaces.pcan import PcanBus

from lan_bus import LANBus

# parse args
parser = argparse.ArgumentParser()
parser.add_argument('--net', default='127.0.0.1')
parser.add_argument('--dest', default='239.0.0.1')
parser.add_argument('--port', default=62222)
parser.add_argument('--seg', default=1)
parser.add_argument('--bitrate', default=125000)
parsed_args = parser.parse_args()


if __name__ == '__main__':
    PCAN_USBBUS_1 = PcanBus(channel='PCAN_USBBUS1', bitrate=parsed_args.bitrate)
    PCAN_USBBUS_2 = PcanBus(channel='PCAN_USBBUS2', bitrate=parsed_args.bitrate)
    LAN_BUS = LANBus(port=parsed_args.port, dest=parsed_args.dest)

    def display_sent(msg, from_bus, to_bus):
        time = datetime.now().time()
        s = f'{time} \t{str(from_bus):<12} => {str(to_bus):<12}'
        print(s)

    def fwd_to_lan(can_bus):
        while True:
            msg: can.Message = can_bus.recv()
            if msg.error_state_indicator or msg.is_error_frame:
                continue
            last_digit_of_channel_name = int(can_bus.channel_info[-1])
            LAN_BUS.send(msg, last_digit_of_channel_name)
            display_sent(msg, from_bus=can_bus, to_bus=LAN_BUS)


    def fwd_to_can():
        while True:
            msgs = LAN_BUS.recv()
            for msg, marker in msgs:
                if marker == 1 or marker == 3:
                    PCAN_USBBUS_1.send(msg)
                    display_sent(msg, from_bus=LAN_BUS, to_bus=PCAN_USBBUS_1)
                if marker == 2 or marker == 3:
                    PCAN_USBBUS_2.send(msg)
                    display_sent(msg, from_bus=LAN_BUS, to_bus=PCAN_USBBUS_2)
                else:
                    pass


    def bridge():
        Thread(target=fwd_to_lan, args=(PCAN_USBBUS_1,), daemon=True)
        Thread(target=fwd_to_lan, args=(PCAN_USBBUS_2,), daemon=True).start()
        Thread(target=fwd_to_can, daemon=True).start()
        input('Press enter to exit\n')


    print('bridging...')
    bridge()
