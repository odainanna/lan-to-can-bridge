# pip install pythoncan msgpack uptime

import argparse
import logging
import re
from datetime import datetime
from threading import Thread

import can
from can.interfaces.pcan import PcanBus

from lan_bus import LANBus

# for printing in colors
from colorama import init
from termcolor import colored

# parse args
parser = argparse.ArgumentParser()
parser.add_argument('--net', default='127.0.0.1')
parser.add_argument('--dest', default='239.0.0.1')
parser.add_argument('--port', default=62222)
parser.add_argument('--seg', default=1)
parser.add_argument('--bitrate', default=125000)
parsed_args = parser.parse_args()

# logging
import logging
import datetime


class CustomFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""
    grey = '\x1b[38;21m'
    black = '\x1b[30;1m'
    red = '\x1b[31;1m'
    bold_red = '\x1b[31;1m'
    green = '\x1b[32;1m'
    blue = '\x1b[34;1m'
    magenta = '\x1b[35;1m'
    cyan = '\x1b[36;1m'
    white = '\x1b[37;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt

    def format(self, record):
        f = lambda color: color + self.fmt + self.reset

        # based on keywords
        logging_format = f(self.black)
        if 'CAN' in record.msg:
            logging_format = f(self.blue)
        elif 'LAN' in record.msg:
            logging_format = f(self.green)

        # based on last integer
        # integers_in_string = list(map(int, re.findall(r'\d+', record.msg)))
        # if integers_in_string:
        #    last_integer_as_color = integers_in_string[-1] % 256
        #    logging_format = f("\x1b[38;5;" + str(last_integer_as_color) + "m ")

        return logging.Formatter(logging_format).format(record)


# Create custom logger logging all five levels
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Define format for logs
fmt = '%(asctime)s | %(message)s'

# Create stdout handler for logging to the console (logs all five levels)
stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(CustomFormatter(fmt))

# Create file handler for logging to a file (logs all five levels)
today = datetime.date.today()
file_handler = logging.FileHandler('my_app_{}.log'.format(today.strftime('%Y_%m_%d')))
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(fmt))

# Add both handlers to the logger
logger.addHandler(stdout_handler)
# logger.addHandler(file_handler)

if __name__ == '__main__':
    can_bus = PcanBus(channel='PCAN_USBBUS1', bitrate=parsed_args.bitrate)
    lan_bus = LANBus(port=parsed_args.port, dest=parsed_args.dest)


    # virtual_bus_1 = can.Bus(interface='virtual', channel='VIRTUAL_1')
    # virtual_bus_2 = can.Bus(interface='virtual', channel='VIRTUAL_2')

    def display_message(msg, receiver, sender, text=''):
        info = f'{datetime.datetime.now().time()} ' \
               f'\t{str(receiver):<12} => {str(sender):<12} ' \
               f'\t{msg.dlc=}' \
               f'\t{msg.data=}' \
               f'\t{msg.is_rx=}' \
               f'\t{hex(msg.arbitration_id)} {text}'

        # debugging info
        hex_id = hex(msg.arbitration_id)
        if hex_id == '0x73c':
            info += '\t <PHYSICAL DPU>'
        elif hex_id == '0x746':
            info += '\t <VIRTUAL DPU>'
        logger.info(info)


    def fwd_to_lan():
        while True:
            msg = can_bus.recv()
            if not msg.is_error_frame and not msg.error_state_indicator:
                lan_bus.send(msg)
                display_message(msg, receiver=can_bus, sender=lan_bus)


    def fwd_to_can():
        while True:
            msgs = lan_bus.recv()
            for msg, marker in msgs:
                can_bus.send(msg)
                display_message(msg, receiver=lan_bus, sender=can_bus)


    def bridge():
        Thread(target=fwd_to_lan, daemon=True).start()
        Thread(target=fwd_to_can, daemon=True).start()
        input('Press enter to exit\n')


    print('bridging...')
    bridge()
