import can

import lan_utils
from lan_utils import FromCanTypeEnum
from lan_utils import LANMessages


class LANBus:
    def __init__(self, dest, port, segment):
        import socket
        import struct

        def create_listener_socket():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', port))
            mreq = struct.pack('=4sl', socket.inet_aton(dest), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            return sock

        self.segment = segment
        self._sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._listener_socket = create_listener_socket()
        self._port = port
        self._dest = dest

        self.channel_id = 'LAN_BUS'

    def recv(self):
        incoming_msg = self._listener_socket.recv(10240)
        # if not (len(incoming_msg) - Header.size()) % lan_utils.Message.size() == 0:
        #    print(f'Ignoring incoming LAN message with length {len(incoming_msg)}.')
        lan_msg_obj = LANMessages.from_bytestring(incoming_msg)
        return lan_msg_obj

    def send(self, can_message: can.Message, marker: int) -> None:
        def bytearrray_to_list(array):
            numeric_data = [0, ] * 64
            for i in range(len(array)):
                numeric_data[i] = int(array[i])
            return tuple(numeric_data)

        if any([can_message.is_extended_id, can_message.is_fd]):
            raise NotImplemented()

        # form the message, flag as forwarded
        header = lan_utils.Header(version=1, vcanmc_hdr_len=8, from_node_id=0, segment=self.segment,
                                  from_can_type=FromCanTypeEnum.CAN,
                                  message_count=1, error_passive=0, bus_off=0)
        can_message = lan_utils.Message(arbitration_id=can_message.arbitration_id,
                                        data=bytearrray_to_list(can_message.data),
                                        dlc=can_message.dlc,
                                        msgCtrl=0,
                                        sec1970=round(can_message.timestamp),
                                        nanoSec=0,
                                        marker=marker,
                                        msgUser=0)
        lan_msgs = LANMessages(header, [can_message])
        self._sender_socket.sendto(lan_msgs.pack(), (self._dest, self._port))

    def __str__(self):
        return self.channel_id

    def status_string(self):
        return ''
