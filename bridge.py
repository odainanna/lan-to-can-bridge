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


def log(*args, **kwargs):
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


def forward_loop(receive_fn, transform_fn, send_fn, comment=''):
    while True:
        incoming_msg = receive_fn()
        outgoing_msg = transform_fn(incoming_msg)
        send_fn(outgoing_msg)
        print(comment)


if __name__ == '__main__':
    configs = can.detect_available_configs(parsed_args.interface)
    print(configs)
    if parsed_args.interface == 'virtual':
        configs = [{'channel': 0}, {'channel': 1}]

    bridge_bus = bus_factory(configs.pop())


    # viewer_bus = bus_factory(configs.pop())
    # can.Notifier([bridge_bus, viewer_bus], [can.Printer()])

    def bridge():
        # setup notifiers
        sock = create_lan_socket()
        lan_thread = Thread(target=forward_loop(lambda: sock.recv(1024),
                                                lambda msg: create_can_msg(msg),
                                                lambda msg: bridge_bus.send(msg), comment="fwd to CAN"), daemon=True,
                            )
        lan_thread.start()

        can_thread = Thread(target=forward_loop(lambda: bridge_bus.recv(),
                                                lambda msg: create_lan_msg(msg),
                                                lambda msg: sock.sendto(msg, (parsed_args.dest, parsed_args.port)),
                                                comment="fwd to LAN"),
                            daemon=True)
        can_thread.start()

        # todo: stay active longer
        time.sleep(1000)


    bridge()
