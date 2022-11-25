# pip install pythoncan msgpack uptime

import argparse
from threading import Thread

import can
from lan_bus import LANBus
from can.interfaces.pcan import PcanBus

# parse args
parser = argparse.ArgumentParser()
parser.add_argument("--dest", default="239.0.0.1")
parser.add_argument("--net", default="127.0.0.1")
parser.add_argument("--seg", default=1)
parser.add_argument("--port", default=62222)
parser.add_argument("--debug", default=True)
parser.add_argument("--interface", default="pcan")
parser.add_argument("--bitrate", default=125000)
parsed_args = parser.parse_args()

# setup python-can
can.rc["interface"] = parsed_args.interface
can.rc["bitrate"] = parsed_args.bitrate


def is_flagged(msg):
    # todo: using id is a quick fix 
    return msg.arbitration_id == 55 

def flag(msg):
    # todo: using id is a quick fix 
    msg.arbitration_id = 55
    return msg


if __name__ == "__main__":
    can_bus = PcanBus(channel="PCAN_USBBUS1", receive_own_messages=False, fd=False)
    lan_bus = LANBus()

    def fwd_to_lan():
        while True:
            msg = can_bus.recv()
            if is_flagged(msg):  # don't forward a forwarded message
                continue
            flag(msg)
            lan_bus.send(msg)
            print("fwd to LAN", msg)

    def fwd_to_can():
        while True:
            msg = lan_bus.recv()
            if is_flagged(msg):
                continue
            flag(msg)
            can_bus.send(msg)
            print(f"fwd to CAN", msg)

    def bridge():
        can_thread = Thread(target=fwd_to_lan, daemon=True)
        can_thread.start()
        lan_thread = Thread(target=fwd_to_can, daemon=True)
        lan_thread.start()
        input()  # exit on enter

    print("bridging...")
    bridge()
