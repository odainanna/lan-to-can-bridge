import can
from can.interfaces.pcan import PcanBus
from can.interfaces.pcan.pcan import PcanCanInitializationError

from lan_bus import LANBus


def create_lan_bus(port, seg):
    return LANBus(port=port, dest='239.0.0.' + str(seg), segment=seg)


def create_pcan_bus(channel, bitrate, dbitrate):
    if dbitrate:
        timing = can.BitTimingFd.from_sample_point(
            f_clock=40_000_000,
            nom_bitrate=bitrate,
            nom_sample_point=80.0,
            data_bitrate=dbitrate,
            data_sample_point=75.0
        )
        return PcanBus(channel=channel, auto_reset=True, timing=timing)
    else:
        return PcanBus(channel=channel, auto_reset=True, bitrate=bitrate, fd=False) 


def create_pcan_buses(bitrate, dbitrate, single=None):
        if single == 1:
            return create_pcan_bus('PCAN_USBBUS1', bitrate, dbitrate), None
        elif single == 2:
            return None, create_pcan_bus('PCAN_USBBUS2', bitrate, dbitrate)
        elif single == 3:
            return create_pcan_bus('PCAN_USBBUS1', bitrate, dbitrate), create_pcan_bus('PCAN_USBBUS2', bitrate,
                                                                                       dbitrate)
        else:
            raise ValueError('single argument must be 1, 2, or 3')

