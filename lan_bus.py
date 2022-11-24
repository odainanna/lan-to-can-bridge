from typing import Tuple, Optional
import can
from can import Message
from message_utils import LANMessage, bytearrray_to_list


class LANBus(can.BusABC):
    def __init__(
        self,
        dest="239.0.0.1",
        port=62222,
        channel=None,
        can_filters: Optional[can.typechecking.CanFilters] = None,
        **kwargs: object
    ):
        import socket
        import struct

        def create_lan_socket():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", port))
            mreq = struct.pack("4sl", socket.inet_aton(dest), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            multicast_ttl = 2
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, multicast_ttl)
            return sock

        self._sock = create_lan_socket()
        self._port = port
        self._dest = dest
        self.channel = "LAN"

    def _recv_internal(
        self, timeout: Optional[float]
    ) -> Tuple[Optional[Message], bool]:
        return None, False

    def recv(self, timeout: Optional[float] = None) -> Optional[Message]:
        incoming_msg = self._sock.recv(1024)
        lan_msg_obj = LANMessage.from_bytestring(incoming_msg)
        transformed_msg = can.Message(
            # timestamp=0.0, todo: fix
            arbitration_id=lan_msg_obj.arbitration_id,
            is_extended_id=False,  # 11 bit
            is_remote_frame=False,  # not implemented
            is_error_frame=False,  # not implemented
            channel=None,
            dlc=lan_msg_obj.dlc,
            data=lan_msg_obj.data[:lan_msg_obj.dlc],
            check=True)
        return transformed_msg

    def send(self, msg: can.Message, timeout: Optional[float] = None):
        if msg.is_extended_id:
            raise NotImplementedError()
        if msg.is_remote_frame:
            raise NotImplementedError()
        if msg.is_error_frame:
            pass
        if msg.is_fd:  # todo?
            raise NotImplementedError()
        if msg.bitrate_switch:
            raise NotImplementedError()
        if msg.error_state_indicator:
            raise NotImplementedError()

        lan_msg_object = LANMessage(
            arbitration_id=msg.arbitration_id,
            dlc=msg.dlc,
            data=bytearrray_to_list(msg.data),
        )
        lan_msg_bytestring = lan_msg_object.to_bytestring()
        self._sock.sendto(lan_msg_bytestring, (self._dest, self._port))
