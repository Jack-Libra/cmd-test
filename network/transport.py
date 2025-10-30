import socket
import logging
from typing import Optional

class UDPTransport:
    """UDP 傳輸層"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.logger = logging.getLogger(__name__)
    
    def open(self) -> bool:
        """開啟 UDP Socket"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.host, self.port))
            self.sock.settimeout(1.0)
            self.logger.info(f"UDP Socket 已開啟: {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"開啟 Socket 失敗: {e}")
            return False
    
    def close(self):
        """關閉 Socket"""
        if self.sock:
            self.sock.close()
            self.sock = None
            self.logger.info("UDP Socket 已關閉")
    
    def send(self, data: bytes, addr: tuple) -> bool:
        """發送資料"""
        if not self.sock:
            return False
        try:
            self.sock.sendto(data, addr)
            self.logger.debug(f"發送 {len(data)} bytes to {addr}")
            return True
        except Exception as e:
            self.logger.error(f"發送失敗: {e}")
            return False
    
    def recv(self) -> Optional[tuple[bytes, tuple]]:
        """接收資料，返回 (data, address) 或 None"""
        if not self.sock:
            return None
        try:
            data, addr = self.sock.recvfrom(4096)
            self.logger.debug(f"收到 {len(data)} bytes from {addr}")
            return data, addr
        except socket.timeout:
            return None
        except Exception as e:
            self.logger.error(f"接收失敗: {e}")
            return None