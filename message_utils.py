from dataclasses import dataclass, astuple
from struct import unpack, pack

import can


@dataclass(frozen=False)
class LANMessage:
    # header
    _: int = 0
    vcanmc_hdr_len: int = 8
    from_node_id: int = 0
    segment: int = 0
    from_can_type: int = 0
    message_count: int = 0
    error_passive: int = 0
    bus_off: int = 0

    # content
    arbitration_id: int = 0
    data: tuple = (0,) * 64
    dlc: int = 1
    msgCtrl: int = 0
    sec1970: int = 0
    nanoSec: int = 0
    msgUser: int = 0
    msgMarker: int = 0

    def __post_init__(self):
        assert not isinstance(self.data, bytearray)
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
        padded_data = self.data + (0,) * (len(self.data) - 64)
        return pack('8B L 64B 2B 4L', *vals[:9], *padded_data, *vals[10:])


def bytearrray_to_list(array):
    # from bytearray to list of ints
    numeric_data = [0, ] * 64
    for i in range(len(array)):
        numeric_data[i] = int(array[i])
    return tuple(numeric_data)


def create_lan_msg(msg: can.Message) -> bytes:
    return LANMessage(arbitration_id=msg.arbitration_id, dlc=msg.dlc,
                      data=bytearrray_to_list(msg.data)).to_bytestring()


def create_can_msg(bytestring):
    lan_msg_obj = LANMessage.from_bytestring(bytestring)
    return can.Message(
        # timestamp=0.0, todo: fix
        arbitration_id=lan_msg_obj.arbitration_id,
        is_extended_id=False,  # 11 bit
        is_remote_frame=False,  # not implemented
        is_error_frame=False,  # not implemented
        channel=None,
        dlc=lan_msg_obj.dlc,
        data=lan_msg_obj.data[:lan_msg_obj.dlc],
        check=True)


if __name__ == "__main__":
    example_bytes = b'\x01\x08<\x01\x02\x01\x00\x00<\x07\x00\x00\x7f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00'

    kwargs = dict(arbitration_id=3, data=[17, 21, 3], dlc=3)
    can_msg = can.Message(**kwargs)
    lan_msg = LANMessage(**kwargs)


    def assert_messages_are_similar(can_msg: can.Message, lan_msg: LANMessage):
        assert can_msg.arbitration_id == lan_msg.arbitration_id
        assert can_msg.dlc == lan_msg.dlc
        assert can_msg.data == bytearray(lan_msg.data)
        # todo: more requirements?


    assert_messages_are_similar(can_msg, lan_msg)
