from dataclasses import dataclass, astuple
from struct import unpack, pack

import can


@dataclass(frozen=False)
class LANMessage:
    # header
    unused: int = 1
    vcanmc_hdr_len: int = 8
    from_node_id: int = 70
    segment: int = 1
    from_can_type: int = 2
    message_count: int = 1
    error_passive: int = 0
    bus_off: int = 0

    # content
    arbitration_id: int = 1862
    data: tuple = (0,) * 64
    dlc: int = 1
    msgCtrl: int = 0
    sec1970: int = 0
    nanoSec: int = 0
    msgUser: int = 0
    msgMarker: int = 3

    def data(self, pad=False):
        if not pad:
            return self.data[: self.dlc]
        else:
            return self.data + (0,) * (len(self.data) - 64)

    @staticmethod
    def from_bytestring(bytestring):
        vals = unpack("8B L 64B 2B 4L", bytestring)
        return LANMessage(*vals[:9], vals[9:73], *vals[73:])

    def to_bytestring(self):
        vals = astuple(self)
        padded_data = self.data + ((0,) * (64 - len(self.data)))
        return pack("8B L 64B 2B 4L", *vals[:9], *padded_data, *vals[10:])


if __name__ == "__main__":
    from constants import SAMPLE_BYTES

    # check conversion
    assert LANMessage.from_bytestring(SAMPLE_BYTES).to_bytestring() == SAMPLE_BYTES

    # check that messages are similar
    kwargs = dict(arbitration_id=3, data=[17, 21, 3], dlc=3)
    can_msg = can.Message(**kwargs)
    lan_msg = LANMessage(**kwargs)

    def assert_messages_are_similar(can_msg: can.Message, lan_msg: LANMessage):
        for key, val in kwargs.items():
            if key == "data":
                assert can_msg.data == bytearray(lan_msg.data)
                continue
            else:
                assert getattr(can_msg, key) == val, f"{getattr(can_msg, key)} {val}"
                assert getattr(lan_msg, key) == val, f"{getattr(lan_msg, key)} {val}"
                # and consequently equal to each other

    assert_messages_are_similar(can_msg, lan_msg)
