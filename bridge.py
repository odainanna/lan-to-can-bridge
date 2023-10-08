import traceback
from threading import Thread

import can
from can.interfaces.pcan.pcan import PcanBus, PcanCanOperationError, PcanCanInitializationError

from lan_bus import LANBus
from lan_utils import FromCanTypeEnum, MarkerEnum


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


def create_pcan_bus(channel, bitrate, dbitrate):
    if dbitrate:
        timing = can.BitTimingFd.from_sample_point(
            f_clock=40_000_000,
            nom_bitrate=bitrate,
            nom_sample_point=80.0,
            data_bitrate=dbitrate,
            data_sample_point=75.0
        )
        bus_kwargs = dict(auto_reset=True, timing=timing)
    else:
        bus_kwargs = dict(auto_reset=True, bitrate=bitrate, fd=False)
    try:
        return PcanBus(channel=channel, **bus_kwargs)
    except PcanCanInitializationError:
        return None


def batch_create_pcan_buses(bitrate, dbitrate, single=None):
    try:
        if single == 1:
            return create_pcan_bus('PCAN_USBBUS1', bitrate, dbitrate), None
        elif single == 2:
            return None, create_pcan_bus('PCAN_USBBUS2', bitrate, dbitrate)
        else:
            return create_pcan_bus('PCAN_USBBUS1', bitrate, dbitrate), create_pcan_bus('PCAN_USBBUS2', bitrate,
                                                                                       dbitrate)
    except PcanCanInitializationError:
        return None, None


def create_lan_bus(port, seg):
    return LANBus(port=port, dest='239.0.0.' + str(seg), segment=seg)


class ChannelInfo:
    """A wrapper for can.Bus objects"""

    def __init__(self, channel, name, marker=None):
        self.rx = 0
        self.tx = 0
        self.channel = channel
        self.name = name
        self.marker = marker

    def recv(self):
        msg = self.channel.recv()
        return msg


class LanChannelInfo(ChannelInfo):
    def send(self, msg, marker):
        self.channel.send(msg, marker=marker)
        self.tx += 1


class PcanChannelInfo(ChannelInfo):

    def send(self, msg: can.Message):
        try:
            self.channel.send(msg)
            self.tx += 1
        except can.interfaces.pcan.pcan.PcanCanOperationError as e:
            traceback.print_exc()


class Bridge:
    def __init__(self, lan_bus, c_1=None, c_2=None):
        self.lan_channel = LanChannelInfo(lan_bus, 'LAN')
        self.can_channels = []
        if c_1:
            self.can_1 = PcanChannelInfo(c_1, c_1.channel_info, marker=1)
            self.can_channels.append(self.can_1)
        else:
            self.can_1 = None
        if c_2:
            self.can_2 = PcanChannelInfo(c_2, c_2.channel_info, marker=2)
            self.can_channels.append(self.can_2)
        else:
            self.can_2 = None
        self.channels = self.can_channels + [self.lan_channel]
        self.fd = (c_1 is not None and c_1.fd) or (c_2 is not None and c_2.fd)
        self.start()

    def listen_to_can(self, can_channel):
        while True:
            try:
                msg: can.Message = can_channel.recv()
            except PcanCanOperationError as e:
                traceback.print_exc()
                return
            if msg.error_state_indicator or msg.is_error_frame:
                continue
            can_channel.rx += 1
            self.lan_channel.send(msg, marker=can_channel.marker)

    def listen_to_lan(self):
        while True:
            lan_msg_obj = self.lan_channel.recv()
            # if a lan message is marked "from can", assume it has been forwarded already and do not
            # forward
            message_has_been_forwarded_already = (lan_msg_obj.header.from_can_type == FromCanTypeEnum.CAN.value)
            if message_has_been_forwarded_already:
                continue
            for lan_msg in lan_msg_obj.messages:
                self.lan_channel.rx += 1
                lan_msg.arbitration_id &= 0xfff
                can_message = create_can_msg(lan_msg, self.fd)
                if self.can_1 and (lan_msg.marker == MarkerEnum.CAN_1.value or lan_msg.marker == MarkerEnum.BOTH.value):
                    self.can_1.send(can_message)
                if self.can_2 and (lan_msg.marker == MarkerEnum.CAN_2.value or lan_msg.marker == MarkerEnum.BOTH.value):
                    self.can_2.send(can_message)

    def stats(self):
        return [['', *[c.name for c in self.channels]],
                ['RX', *[c.rx for c in self.channels]],
                ['TX', *[c.tx for c in self.channels]]]

    def start(self):
        for c in self.can_channels:
            Thread(target=self.listen_to_can, args=(c,), daemon=True).start()
        Thread(target=self.listen_to_lan, daemon=True).start()
