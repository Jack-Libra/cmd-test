# network/udp_transport.py
"""
UDP傳輸層
"""

import socket
import logging
from typing import Optional
from .buffer import PacketBuffer

class UDPTransport:
    """UDP傳輸層"""
    
    def __init__(self, local_ip: str, local_port: int, 
                 server_ip: str, server_port: int):
        self.local_addr = (local_ip, local_port)
        self.server_addr = (server_ip, server_port)
        self.socket: Optional[socket.socket] = None
        self.buffer = PacketBuffer()
        self.logger = logging.getLogger(__name__)
    
    def open(self) -> bool:
        """開啟UDP連接"""
        if self.socket:
            self.close()
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 允許重複使用地址
            
            self.socket.bind(self.local_addr)
            self.socket.settimeout(1.0)
            self.buffer.buffer.clear()
            self.logger.info(f"開啟UDP連接: {self.local_addr[0]}:{self.local_addr[1]}")
            return True
        except Exception as e:
            self.logger.error(f"開啟UDP連接失敗: {e}")
            return False
    
    def close(self):
        """關閉UDP連接"""
        if self.socket:
            self.socket.close()
            self.socket = None
            self.logger.info("UDP連接已關閉")
    
    def receive_data(self):
        """接收數據"""
        if not self.socket:
            return b"", None
        
        try:
            data, addr = self.socket.recvfrom(4096) # 4KB
            return data, addr
        except socket.timeout:
            return b"", None
        except Exception as e:
            self.logger.error(f"接收數據失敗: {e}")
            return b"", None
    
    def send_data(self, data: bytes) -> bool:
        """發送數據"""
        if not self.socket:
            self.logger.error("尚未開啟UDP連接")
            return False
        
        try:
            self.socket.sendto(data, self.server_addr)
            self.logger.debug(f"發送數據到 {self.server_addr[0]}:{self.server_addr[1]}")
            return True
        except Exception as e:
            self.logger.error(f"發送數據失敗: {e}")
            return False
    
    def process_buffer(self, data: bytes) -> list:
        """處理緩衝區數據，返回完整封包列表"""
        return self.buffer.feed(data)