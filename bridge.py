from threading import Thread

import can
from can.interfaces.pcan.pcan import PcanBus, PcanCanOperationError

from lan_bus import LANBus
from lan_utils import FromCanTypeEnum, MarkerEnum

log = print


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
        self.rx = {self.bus_1.channel_info: 0, self.bus_2.channel_info: 0, self.lan_bus.channel_info: 0}
        self.tx = {self.bus_1.channel_info: 0, self.bus_2.channel_info: 0, self.lan_bus.channel_info: 0}

        assert self.bus_1.fd == self.bus_2.fd
        self.fd = self.bus_1.fd
        self.start()

    @staticmethod
    def detect():
        return can.detect_available_configs('pcan')

    def listen_to_can(self, can_bus):
        # log(f'listening to {can_bus}')
        while True:
            try:
                msg: can.Message = can_bus.recv()
            except PcanCanOperationError as e:
                log(f'{self.lan_bus} got error {e}')
                return
            if msg.error_state_indicator or msg.is_error_frame:
                continue
            marker = int(can_bus.channel_info[-1])  # the last digit of the channel name
            self.lan_bus.send(msg, marker=marker)
            self.rx[can_bus.channel_info] += 1
            self.tx[self.lan_bus.channel_info] += 1
            log(f'{self.lan_bus} sent {msg}')

    def _send(self, can_bus, msg: can.Message):
        try:
            can_bus.send(msg)
        except can.interfaces.pcan.pcan.PcanCanOperationError as e:
            log('ERROR:', e)

    def listen_to_lan(self):
        # log(f'listening to {self.lan_bus}')
        while True:
            lan_msg_obj = self.lan_bus.recv()
            # if a lan message is marked "from can", assume it has been forwarded already and do not
            # forward
            message_has_been_forwarded_already = (lan_msg_obj.header.from_can_type == FromCanTypeEnum.CAN.value)
            if message_has_been_forwarded_already:
                continue
            log(f'rcv {lan_msg_obj} on {self.lan_bus}')
            for lan_msg in lan_msg_obj.messages:
                lan_msg.arbitration_id &= 0xfff
                can_message = create_can_msg(lan_msg, self.fd)
                self.rx[self.lan_bus.channel_info] += 1
                if lan_msg.marker == MarkerEnum.CAN_1.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    self._send(self.bus_1, can_message)
                    self.tx[self.bus_1.channel_info] += 1
                    log(f'sent {can_message} on bus 1')
                if lan_msg.marker == MarkerEnum.CAN_2.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    self._send(self.bus_2.channel_info, can_message)
                    self.tx[self.bus_2] += 1
                    log(f'sent {can_message} on bus 2')

    def stats(self):
        return [['', 'CAN 1', 'CAN 2', 'LAN'], ['RX', *self.rx.values()], ['TX', *self.tx.values()]]

    def start(self):
        Thread(target=self.listen_to_can, args=(self.bus_1,), daemon=True).start()
        Thread(target=self.listen_to_can, args=(self.bus_2,), daemon=True).start()
        Thread(target=self.listen_to_lan, daemon=True).start()
