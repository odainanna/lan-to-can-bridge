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
            f_clock=80_000_000,
            nom_bitrate=bitrate,
            nom_sample_point=81.3,
            data_bitrate=dbitrate,
            data_sample_point=80.0,
        )
        bus_kwargs = dict(auto_reset=True, timing=timing)
    else:
        bus_kwargs = dict(auto_reset=True, bitrate=bitrate, fd=False)
    try:
        return PcanBus(channel=channel, **bus_kwargs)
    except PcanCanInitializationError:
        return None


def batch_create_pcan_buses(bitrate, dbitrate, single=None):
    available_channels = can.detect_available_configs('pcan')
    if single == 1:
        selected_channels = [available_channels[0]]
    elif single == 2:
        selected_channels = [available_channels[1]]
    else:
        selected_channels = available_channels
    return [create_pcan_bus(x['channel'], bitrate, dbitrate) for x in selected_channels]


def batch_create_pcan_bus(bitrate, dbitrate, single=None):
    channel_info = can.detect_available_configs('pcan')
    try:
        if single == 1:  # just the first channel
            return [create_pcan_bus(channel_info[0]['channel'], bitrate, dbitrate), None]
        elif single == 2:
            return [None, create_pcan_bus(channel_info[1]['channel'], bitrate, dbitrate)]
        else:
            return [create_pcan_bus(x['channel'], bitrate, dbitrate) for x in channel_info]
    except IndexError:
        return []


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
        self.rx += 1
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

    def __init__(self, lan_bus, *can_channels):
        self.lan_channel = LanChannelInfo(lan_bus, 'LAN')
        self.can_channels = [PcanChannelInfo(can_channels[i],
                                             'CAN ' + str(i + 1), marker=i + 1) for i in range(len(can_channels))]
        self.channels = self.can_channels + [self.lan_channel]
        self.fd = False

        try:
            self.fd = any(x.fd for x in can_channels)
        except AttributeError:
            self.fd = False
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
                lan_msg.arbitration_id &= 0xfff
                can_message = create_can_msg(lan_msg, self.fd)
                if lan_msg.marker == MarkerEnum.CAN_1.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    self.can_channels[0].send(can_message)
                if lan_msg.marker == MarkerEnum.CAN_2.value or lan_msg.marker == MarkerEnum.BOTH.value:
                    self.can_channels[1].send(can_message)

    def stats(self):
        return [['', *[c.name for c in self.channels]],
                ['RX', *[c.rx for c in self.channels]],
                ['TX', *[c.tx for c in self.channels]]]

    def start(self):
        for c in self.can_channels:
            Thread(target=self.listen_to_can, args=(c,), daemon=True).start()
        Thread(target=self.listen_to_lan, daemon=True).start()
