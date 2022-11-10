from struct import unpack
from dataclasses import dataclass

@dataclass(frozen=True)
class DecodedMessage:
    # header
    _: int
    vcanmc_hdr_len: int
    from_node_id: int
    segment: int
    from_can_type: int
    message_count: int
    error_passive: int
    bus_off: int

    # content
    identifier: int
    data: tuple
    msgDLC: int
    msgCtrl: int
    sec1970: int  # timestamp
    nanoSec: int  # timestamp
    msgUser: int
    msgMarker: int

    @staticmethod
    def frombytes(bytes):
        format = 'BBBBBBBB L64B2B4L'
        vars = unpack(format, bytes)
        data = vars[9:73]
        return DecodedMessage(*vars[:9], data, *vars[73:])


if __name__ == '__main__':
    example_message = b'\x01\x08<\x01\x02\x01\x00\x00<\x07\x00\x00\x7f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00'
    header_values = (1, 8, 60, 1, 2, 1, 0, 0)
    message_values = (1852, (
        127, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), 1, 0, 0, 0, 0, 3)

    assert DecodedMessage(*header_values, *message_values) == DecodedMessage.frombytes(example_message)
    print(DecodedMessage.frombytes(example_message))