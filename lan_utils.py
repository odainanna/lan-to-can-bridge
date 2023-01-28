import struct
from dataclasses import dataclass
from enum import Enum
from struct import pack


class FromCanTypeEnum(Enum):
    CAN = 0
    VCAN = 1


class MarkerEnum(Enum):
    CAN_1 = 1
    CAN_2 = 2
    BOTH = 3


@dataclass(frozen=False)
class Header:
    version: int
    vcanmc_hdr_len: int
    from_node_id: int
    segment: int
    from_can_type: FromCanTypeEnum
    message_count: int
    error_passive: int
    bus_off: int

    @staticmethod
    def fmt():
        return '8B'

    @staticmethod
    def size():
        return 8  # struct.calcsize(Header.fmt())

    def pack(self):
        return pack(self.fmt(), self.version, self.vcanmc_hdr_len, self.from_node_id, self.segment,
                    self.from_can_type.value, self.message_count, self.error_passive, self.bus_off)


@dataclass(frozen=False)
class Message:
    arbitration_id: int
    data: tuple
    dlc: int
    msgCtrl: int
    sec1970: int
    nanoSec: int
    msgUser: int
    marker: int

    @staticmethod
    def fmt():
        return 'L64B2B4L'

    @staticmethod
    def size():
        return struct.calcsize(Message.fmt())

    def pack(self):
        return struct.pack(self.fmt(), self.arbitration_id, *self.data, self.dlc, self.msgCtrl, self.sec1970,
                           self.nanoSec, self.msgUser, self.marker)


@dataclass(frozen=False)
class LANMessages:
    header: Header
    messages: list

    @staticmethod
    def from_bytestring(bytestring):
        header = Header(*struct.unpack_from(Header.fmt(), bytestring))
        messages = []
        for message_values in struct.iter_unpack(Message.fmt(), bytestring[Header.size():]):
            message_values = list(message_values)
            message_values[1:65] = [message_values[1:65]]  # data as list
            messages.append(Message(*message_values))
        return LANMessages(header, messages)

    def pack(self):
        return self.header.pack() + b''.join([msg.pack() for msg in self.messages])


if __name__ == '__main__':
    SAMPLE_BYTES = b"\x01\x08F\x01\x02\x01\x00\x00F\x07\x00\x00\x7f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00"

    # check conversion
    assert LANMessages.from_bytestring(SAMPLE_BYTES).pack() == SAMPLE_BYTES
