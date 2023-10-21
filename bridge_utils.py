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
        bus_kwargs = dict(auto_reset=True, timing=timing)
    if bitrate == 125000 and dbitrate == 125000:
        timing = can.BitTimingFd(
            f_clock=40_000_000,
            nom_brp=8, nom_tseg1=29, nom_tseg2=10, nom_sjw=10,
            data_brp=8, data_tseg1=31, data_tseg2=8, data_sjw=8
        )
        bus_kwargs = dict(auto_reset=True, timing=timing)
    elif bitrate == 250000 and dbitrate == 1000000:
        timing = can.BitTimingFd(
            f_clock=40_000_000,
            nom_brp=1, nom_tseg1=127, nom_tseg2=32, nom_sjw=32,
            data_brp=1, data_tseg1=31, data_tseg2=8, data_sjw=8
        )
        bus_kwargs = dict(auto_reset=True, timing=timing)
    else:
        bus_kwargs = dict(auto_reset=True, bitrate=bitrate, fd=False)
    try:
        return PcanBus(channel=channel, **bus_kwargs)
    except PcanCanInitializationError:
        return None


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

