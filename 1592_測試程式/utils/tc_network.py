"""
號誌控制系統網路通訊功能
"""
import socket
import binascii
from .tc_core import *
from .log_setup import *
from .tc_protocol import TrafficControlProtocol

class TCNetwork:
    """交通控制網路通訊"""
    
    def __init__(self, local_ip, local_port, server_ip, server_port):
        self.local_addr = (local_ip, local_port)
        self.server_addr = (server_ip, server_port)
        self.socket = None
        self.protocol = TrafficControlProtocol()
        self.buffer = bytearray()
        self.last_client_addr = None
        log_info(f"初始化網路: 本地={local_ip}:{local_port}, 伺服器={server_ip}:{server_port}")
    
    def open(self):
        """開啟 UDP 連接"""
        if self.socket:
            self.close()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(self.local_addr)
            self.socket.settimeout(1.0)
            self.buffer.clear()
            log_info(f"開啟 UDP 連接: {self.local_addr[0]}:{self.local_addr[1]}")
            return True
        except Exception as e:
            log_error(f"開啟 UDP 連接失敗: {e}")
            return False
    
    def receive_data(self):
        """接收資料"""
        if not self.socket:
            return b"", None
        
        try:
            data, addr = self.socket.recvfrom(4096)
            # log_info(f'收到原始封包: {binascii.hexlify(data).decode()}')
            self.last_client_addr = addr
            return data, addr
        except socket.timeout:
            return b"", None
        except Exception as e:
            log_error(f"接收資料失敗: {e}")
            return b"", None
    
    def process_buffer(self, data):
        """處理緩衝區資料"""
        self.buffer.extend(data)
        packets, self.buffer = self.protocol.parse_buffer(self.buffer)
        return packets
    
    def process_packet(self, packet):
        """處理封包給協議層並發送 ACK"""
        if not packet:
            return
            
        command = packet.get("command", "")
        self.protocol.process_packet(packet)

        # 對所有封包發送 ACK
        if self.last_client_addr:
            self.send_ack(packet)
    
    def send_ack(self, packet):
        """發送 ACK 確認封包"""
        try:
            seq = packet.get('seq', 0)
            tc_id = packet.get('tc_id', 0)
            command = packet.get("command", "")
            
            ack_packet = self.protocol.create_ack_packet(seq, tc_id)
            
            if ack_packet and self.last_client_addr and command not in ["0F80", "0F81"]:
                self.socket.sendto(ack_packet, self.last_client_addr)

        except Exception as e:
            log_error(f"發送 ACK 失敗: {e}")
    
    def send_packet(self, packet):
        """發送封包"""
        if not self.socket:
            log_error("尚未開啟 UDP 連接")
            return False

        try:
            self.socket.sendto(packet, self.server_addr)
            log_info(f"發送封包到 {self.server_addr[0]}:{self.server_addr[1]}: {binascii.hexlify(packet).decode('ascii')}")
            return True
        except Exception as e:
            log_error(f"發送封包失敗: {e}")
            return False
    
    def close(self):
        """關閉 UDP 連接"""
        if self.socket:
            self.socket.close()
            self.socket = None
            log_info("UDP 連接已關閉")
            