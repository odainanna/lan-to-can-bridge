# pip install pythoncan msgpack uptime

import argparse
from threading import Thread

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
    can_bus = PcanBus(channel='PCAN_USBBUS1', bitrate=parsed_args.bitrate)
    lan_bus = LANBus(port=parsed_args.port, dest=parsed_args.dest)


    def fwd_to_lan():
        while True:
            msg = can_bus.recv()
            lan_bus.send(msg)


    def fwd_to_can():
        while True:
            msgs = lan_bus.recv()
            for msg in msgs:
                can_bus.send(msg)


    def bridge():
        Thread(target=fwd_to_lan, daemon=True).start()
        Thread(target=fwd_to_can, daemon=True).start()
        input('Press enter to exit')  # exit on enter


    print('bridging...')
    bridge()
