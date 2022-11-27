from typing import Optional

import can
from can import Message

import lan_message
from lan_message import LANMessages, Header


class LANBus:
    def __init__(
            self,
            dest='239.0.0.1',
            port=62222,
    ):
        import socket
        import struct

        def create_listener_socket():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', port))
            mreq = struct.pack('=4sl', socket.inet_aton(dest), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            return sock

        self._sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._listener_socket = create_listener_socket()
        self._port = port
        self._dest = dest

    def recv(self, timeout: Optional[float] = None) -> list[Message] | None:
        incoming_msg = self._listener_socket.recv(10240)
        if not (len(incoming_msg) - Header.size()) % lan_message.Message.size() == 0:
            print(f'Ignoring incoming LAN message with length {len(incoming_msg)}.')

        lan_msg_obj = LANMessages(incoming_msg)

        if lan_msg_obj.is_flagged:
            return []

        return [can.Message(
            timestamp=msg.sec1970,
            arbitration_id=msg.arbitration_id,
            is_extended_id=False,  # 11 bit
            is_remote_frame=False,  # not implemented
            is_error_frame=False,  # not implemented
            channel=None,
            dlc=msg.dlc,
            data=msg.data[: msg.dlc],
            check=True,
        ) for msg in lan_msg_obj.messages]

    def send(self, msg: can.Message, timeout: Optional[float] = None):
        def bytearrray_to_list(array):
            numeric_data = [0, ] * 64
            for i in range(len(array)):
                numeric_data[i] = int(array[i])
            return tuple(numeric_data)

        if any([msg.is_extended_id, msg.is_fd]):
            raise NotImplemented()

        # form the message
        lan_msg_object = LANMessages(
            sec1970=round(msg.timestamp),
            arbitration_id=msg.arbitration_id,
            dlc=msg.dlc,
            data=bytearrray_to_list(msg.data),
        )

        # flag the message as forwarded
        lan_msg_object.flag()

        self._sender_socket.sendto(lan_msg_object.pack(), (self._dest, self._port))
