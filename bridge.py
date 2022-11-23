# pip install pythoncan msgpack uptime

import argparse
import socket
import struct
import time
from threading import Thread

import can

from message_utils import create_can_msg, create_lan_msg

parser = argparse.ArgumentParser()
parser.add_argument('--dest', default='239.0.0.1')
parser.add_argument('--net', default='127.0.0.1')
parser.add_argument('--seg', default=1)
parser.add_argument('--port', default=62222)
parser.add_argument('--debug', default=True)

parser.add_argument('--interface', default='pcan')
parser.add_argument('--bitrate', default=125000)
parsed_args = parser.parse_args()

# can setup
can.rc['interface'] = parsed_args.interface
can.rc['bitrate'] = parsed_args.bitrate


def debug_print(*args, **kwargs):
    """print-like function that only prints in debug mode"""
    if parsed_args.debug:
        print(*args, *kwargs)


def create_lan_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', parsed_args.port))
    mreq = struct.pack('4sl', socket.inet_aton(parsed_args.dest), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    multicast_ttl = 2
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, multicast_ttl)
    return sock


def bus_factory(config):
    if isinstance(config, dict):
        config = config['channel']
    return can.Bus(interface=parsed_args.interface, channel=config, receive_own_messages=False, fd=False)

sock = create_lan_socket()

def fwd_to_lan():
    while True:
        incoming_msg = bridge_bus.recv()
        outgoing_msg = create_lan_msg(incoming_msg)
        sock.sendto(outgoing_msg, (parsed_args.dest, parsed_args.port))
        debug_print("fwd to LAN", outgoing_msg)


def fwd_to_can():
    while True:
        incoming_msg = sock.recv(1024)
        outgoing_msg = create_can_msg(incoming_msg)
        bridge_bus.send(outgoing_msg)
        debug_print(f"fwd to CAN", outgoing_msg)


if __name__ == '__main__':
    # display available configs 
    debug_print(can.detect_available_configs(parsed_args.interface))
    
    bridge_bus = bus_factory('PCAN_USBBUS1')
    def bridge():
        can_thread = Thread(target=fwd_to_lan, daemon=True)                          
        can_thread.start()
        lan_thread = Thread(target=fwd_to_can, daemon=True)
        lan_thread.start()
        input()  # exit on enter

    debug_print('bridging...')
    bridge()
