import logging
from threading import Thread

import can
from can.interfaces.pcan.pcan import PcanBus, PcanCanOperationError

from lan_bus import LANBus
from lan_utils import FromCanTypeEnum, MarkerEnum

# setup logging
logging.basicConfig(level=logging.ERROR)


def create_can_msg(lan_msg, is_fd):
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
        is_fd=is_fd,
    )


class Bridge:
    def __init__(self, bus_1: PcanBus, bus_2: PcanBus, lan_bus: LANBus):
        self.bus_1 = bus_1
        self.bus_2 = bus_2
        self.lan_bus = lan_bus
        self.counter = {self.bus_1.channel_info: 0, self.bus_2.channel_info: 0, self.lan_bus.channel_info: 0}
        assert self.bus_1.fd == self.bus_2.fd
        self.fd = self.bus_1.fd
        self.start()

    @staticmethod
    def detect():
        return can.detect_available_configs('pcan')

    def fwd_to_lan(self, can_bus):
        logging.info(f'listening to {can_bus}')
        while True:
            try:
                msg: can.Message = can_bus.recv()
            except PcanCanOperationError as e:
                logging.error(f'{self.lan_bus} got error {e}')
                return
            if msg.error_state_indicator or msg.is_error_frame:
                continue
            last_digit_of_channel_name = int(can_bus.channel_info[-1])
            self.lan_bus.send(msg, marker=last_digit_of_channel_name)
            self.counter[self.lan_bus.channel_info] += 1
            logging.info(f'{self.lan_bus} sent {msg}')

    def _send(self, can_bus, msg: can.Message):
        try:
            can_bus.send(msg)
            print(can_bus.status())
            logging.info(f'{can_bus} sent {msg}')
            self.counter[can_bus.channel_info] += 1  # counter += 1  todo: multiple messages in one?
            return True
        except can.interfaces.pcan.pcan.PcanCanOperationError as e:
            logging.warning(e)
            return False

    def fwd_to_can(self):
        logging.info(f'listening to {self.lan_bus}')
        while True:
            lan_msg_obj = self.lan_bus.recv()
            # if a lan message is marked "from can", assume it has been forwarded already and do not
            # forward
            message_has_been_forwarded_already = (lan_msg_obj.header.from_can_type == FromCanTypeEnum.CAN.value)
            if message_has_been_forwarded_already:
                continue
            logging.info(f'rcv {lan_msg_obj} on {self.lan_bus}')
            for lan_msg in lan_msg_obj.messages:
                lan_msg.arbitration_id &= 0xfff
                can_message = create_can_msg(lan_msg, self.fd)
                if lan_msg.marker == MarkerEnum.CAN_1.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    self._send(self.bus_1, can_message)
                    logging.info(f'sent {can_message} on bus 1')
                if lan_msg.marker == MarkerEnum.CAN_2.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    self._send(self.bus_2, can_message)
                    logging.info(f'sent {can_message} on bus 2')


    def stats(self):
        return [['BUSES', *self.counter.keys()], ['SENT', *self.counter.values()]]

    def start(self):
        Thread(target=self.fwd_to_lan, args=(self.bus_1,), daemon=True).start()
        Thread(target=self.fwd_to_lan, args=(self.bus_2,), daemon=True).start()
        Thread(target=self.fwd_to_can, daemon=True).start()
