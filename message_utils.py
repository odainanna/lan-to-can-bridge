from dataclasses import dataclass, astuple
from struct import unpack, pack

import can


@dataclass(frozen=False)
class LANMessage:
    # header
    _: int = 1
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

    def __post_init__(self):
        assert self.dlc <= len(self.data) <= 64

    def data(self, pad=False):
        if not pad:
            return self.data[:self.dlc]
        else:
            return self.data + (0,) * (len(self.data) - 64)

    @staticmethod
    def from_bytestring(bytestring):
        vals = unpack('8B L 64B 2B 4L', bytestring)
        return LANMessage(*vals[:9], vals[9:73], *vals[73:])

    def to_bytestring(self):
        vals = astuple(self)
        padded_data = self.data + ((0,) * (64 - len(self.data)))
        return pack('8B L 64B 2B 4L', *vals[:9], *padded_data, *vals[10:])


def bytearrray_to_list(array):
    # from bytearray to list of ints
    numeric_data = [0, ] * 64
    for i in range(len(array)):
        numeric_data[i] = int(array[i])
    return tuple(numeric_data)


if __name__ == "__main__":
    example_bytes = b'\x01\x08<\x01\x02\x01\x00\x00<\x07\x00\x00\x7f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00'

    kwargs = dict(arbitration_id=3, data=[17, 21, 3], dlc=3)

    # check conversion
    assert LANMessage.from_bytestring(example_bytes).to_bytestring() == example_bytes

    can_msg = can.Message(**kwargs)
    lan_msg = LANMessage(**kwargs)

    def assert_messages_are_similar(can_msg: can.Message, lan_msg: LANMessage):
        assert can_msg.arbitration_id == lan_msg.arbitration_id
        assert can_msg.dlc == lan_msg.dlc
        assert can_msg.data == bytearray(lan_msg.data)
        # todo: more requirements?


    assert_messages_are_similar(can_msg, lan_msg)
