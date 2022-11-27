from socket import AF_INET, IP_ADD_MEMBERSHIP, IPPROTO_IP, SOCK_DGRAM, inet_aton
from typing import Tuple, Optional
import can
from can import Message
from lan_message import LANMessage


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

        def create_listener_socket():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", port))
            mreq = struct.pack("=4sl", socket.inet_aton(dest), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            return sock

        self._sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._listener_socket = create_listener_socket()
        self._port = port
        self._dest = dest

    def _recv_internal(
        self, timeout: Optional[float]
    ) -> Tuple[Optional[Message], bool]:
        return None, False

    def recv(self, timeout: Optional[float] = None) -> Optional[Message]:
        incoming_msg = self._listener_socket.recv(10240)
        lan_msg_obj = LANMessage.from_bytestring(incoming_msg)

        transformed_msg = can.Message(
            timestamp=lan_msg_obj.sec1970,
            arbitration_id=lan_msg_obj.arbitration_id,
            is_extended_id=False,  # 11 bit
            is_remote_frame=False,  # not implemented
            is_error_frame=False,  # not implemented
            channel=None,
            dlc=lan_msg_obj.dlc,
            data=lan_msg_obj.data[: lan_msg_obj.dlc],
            check=True,
        )
        return transformed_msg

    def send(self, msg: can.Message, timeout: Optional[float] = None):
        def bytearrray_to_list(array):
            numeric_data = [
                0,
            ] * 64
            for i in range(len(array)):
                numeric_data[i] = int(array[i])
            return tuple(numeric_data)

        if any([msg.is_extended_id, msg.is_fd]):
            raise NotImplemented()

        # form the message
        lan_msg_object = LANMessage(
            sec1970=round(msg.timestamp),
            arbitration_id=msg.arbitration_id,
            dlc=msg.dlc,
            data=bytearrray_to_list(msg.data),
        )

        msg_bytestring = lan_msg_object.to_bytestring()
        self._sender_socket.sendto(msg_bytestring, (self._dest, self._port))
