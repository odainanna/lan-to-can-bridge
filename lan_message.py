import struct
from dataclasses import dataclass, astuple
from struct import pack


@dataclass(frozen=False)
class Header:
    flag: int = 1
    vcanmc_hdr_len: int = 8
    from_node_id: int = 70
    segment: int = 1
    from_can_type: int = 2
    message_count: int = 1
    error_passive: int = 0
    bus_off: int = 0

    @staticmethod
    def fmt():
        return '8B'

    @staticmethod
    def size():
        return 8  # struct.calcsize(Header.fmt())

    def pack(self):
        return pack(self.fmt(), *astuple(self))


@dataclass(frozen=False)
class Message:
    arbitration_id: int
    data: tuple
    dlc: int
    msgCtrl: int
    sec1970: int
    nanoSec: int
    msgUser: int
    msgMarker: int

    @staticmethod
    def fmt():
        return 'L64B2B4L'

    @staticmethod
    def size():
        return struct.calcsize(Message.fmt())

    def pack(self):
        return struct.pack(self.fmt(), self.arbitration_id, *self.data, self.dlc, self.msgCtrl, self.sec1970,
                           self.nanoSec, self.msgUser, self.msgMarker)


@dataclass(frozen=False)
class LANMessages:
    header: Header
    messages: list

    def __init__(self, bytestring=None, **kwargs):
        if bytestring:
            self.header = Header(*struct.unpack_from(Header.fmt(), bytestring))
            self.messages = []
            for message_values in struct.iter_unpack(Message.fmt(), bytestring[Header.size():]):
                message_values = list(message_values)
                message_values[1:65] = [message_values[1:65]]  # data as list
                self.messages.append(Message(*message_values))
        else:
            self.header = Header()
            self.messages = [Message(**kwargs)]

    def pack(self):
        return self.header.pack() + b''.join([msg.pack() for msg in self.messages])

    @property
    def message_count(self):
        return self.header.message_count

    @property
    def is_flagged(self):
        return self.header.flag == 55

    def flag(self):
        self.header.flag = 55


if __name__ == '__main__':
    SAMPLE_BYTES = b"\x01\x08F\x01\x02\x01\x00\x00F\x07\x00\x00\x7f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00"

    # check conversion
    assert LANMessages(SAMPLE_BYTES).pack() == SAMPLE_BYTES
