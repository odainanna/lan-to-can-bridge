import traceback
from threading import Thread

import can
from can.interfaces.pcan import PcanBus
from can.interfaces.virtual import VirtualBus
from lan_bus import LANBus
from lan_utils import MarkerEnum, FromCanTypeEnum


class Channel:
    def __init__(self, bus: VirtualBus or PcanBus or None, name=None, marker=None):
        self.bus = bus
        self.rx = 0
        self.tx = 0
        self.marker = marker
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'Channel: {self.name}'

    def log_rx(self):
        self.rx += 1

    def log_tx(self):
        self.tx += 1

    @property
    def fd(self):
        try:
            return self.bus.fd
        except:
            return False

    def is_active(self):
        return self.bus is not None


class Bridge:

    def __init__(self, lan: LANBus, can_1=None, can_2=None):
        # can_1, can_2 can be Virtual, PcanBus or None
        if can_1 is None and can_2 is None:
            raise ValueError('The bridge requires at least one can channel')
        self.lan = Channel(lan, name='LAN')
        self.can_1 = Channel(can_1, name='CAN 1', marker=1)
        self.can_2 = Channel(can_2, name='CAN 2', marker=2)
        self.all_channels = (self.lan, self.can_1, self.can_2)
        self.active_channels = tuple(c for c in self.all_channels if c.is_active())
        self.fd = (isinstance(can_1, PcanBus) and can_1.fd) or (isinstance(can_2, PcanBus) and can_2.fd)
        self.start()

    def listen_to_can(self, can_channel: Channel):
        while True:
            try:
                msg: can.Message = can_channel.bus.recv()
            except Exception:
                continue
            if msg.error_state_indicator or msg.is_error_frame:
                continue
            can_channel.log_rx()
            self.lan.bus.send(msg, marker=can_channel.marker)
            self.lan.log_tx()

    def listen_to_lan(self):
        while True:
            lan_msg_obj = self.lan.bus.recv()
            # if a lan message is marked "from can", assume it has been forwarded already and do not
            # forward
            message_has_been_forwarded_already = (lan_msg_obj.header.from_can_type == FromCanTypeEnum.CAN.value)
            if message_has_been_forwarded_already:
                continue
            for lan_msg in lan_msg_obj.messages:
                self.lan.log_rx()
                lan_msg.arbitration_id &= 0xfff
                can_message = can.Message(
                    timestamp=lan_msg.sec1970,
                    arbitration_id=lan_msg.arbitration_id,
                    is_extended_id=False,  # 11 bit
                    is_remote_frame=False,
                    is_error_frame=False,
                    channel=None,
                    dlc=lan_msg.dlc,
                    data=lan_msg.data[: lan_msg.dlc],
                    check=True,
                    is_fd=self.fd,
                )
                if lan_msg.marker == MarkerEnum.CAN_1.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    if self.can_1.is_active():
                        self.can_1.bus.send(can_message)
                        self.can_1.log_tx()

                if lan_msg.marker == MarkerEnum.CAN_2.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    if self.can_2.is_active():
                        self.can_2.bus.send(can_message)
                        self.can_2.log_tx()

    def stats(self):
        return [['', *[c.name for c in self.active_channels]],
                ['RX', *[c.rx for c in self.active_channels]],
                ['TX', *[c.tx for c in self.active_channels]]]

    def start(self):
        if self.can_1.is_active():
            Thread(target=self.listen_to_can, args=(self.can_1,), daemon=True).start()
        if self.can_2.is_active():
            Thread(target=self.listen_to_can, args=(self.can_2,), daemon=True).start()
        Thread(target=self.listen_to_lan, daemon=True).start()
