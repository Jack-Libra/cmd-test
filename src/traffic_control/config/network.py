# config/network.py
"""
UDP傳輸層
"""

import socket
import binascii
import struct
from typing import Protocol, Tuple, Optional
#from abc import ABC, abstractmethod


# 避免 mode class 碰到Transport實例
# 放便後續新增TCPTransport
class NetworkTransport(Protocol):
    """網絡傳輸協議接口"""
    def open(self) -> bool: ...
    def close(self) -> None: ...
    def send_data(self, data: bytes, addr: Optional[Tuple[str, int]] = None) -> bool: ...
    def receive_data(self) -> Tuple[bytes, Optional[Tuple[str, int]]]: ...
    def process_buffer(self, data: bytes) -> list: ...

class UDPTransport:
    """UDP傳輸層"""
    
    def __init__(self, local_ip, local_port, 
                 server_ip, server_port, logger):
        self.local_addr = (local_ip, local_port)
        self.server_addr = (server_ip, server_port)
        self.socket = None
        self.buffer = PacketBuffer(logger)
        self.logger = logger
    
    def open(self):
        """開啟UDP連接"""
        if self.socket:
            self.close()
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
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
    
    def send_data(self, data, addr: Optional[Tuple[str, int]] = None):
        """發送數據"""
        if not self.socket:
            self.logger.error("尚未開啟UDP連接")
            return False
        target_addr = addr if addr is not None else self.server_addr
        try:
            self.socket.sendto(data, target_addr)
            #self.logger.info(f"發送數據到 {target_addr[0]}:{target_addr[1]}")
            return True
        except Exception as e:
            self.logger.error(f"發送數據失敗: {e}")
            return False
    
    def process_buffer(self, data):
        """處理緩衝區數據，返回完整封包列表"""
        return self.buffer.feed(data)

# 待實現
class MulticastUDPTransport:
    """Multicast UDP傳輸層"""
    
    def __init__(self, local_ip, local_port, 
                 server_ip, server_port, logger,
                 multicast_group=None, multicast_ttl=1):
        """
        初始化UDP傳輸層
        
        Args:
            local_ip: 本地IP地址
            local_port: 本地端口
            server_ip: 服務器IP地址（或multicast地址）
            server_port: 服務器端口
            logger: 日誌記錄器
            multicast_group: Multicast組地址（例如 "224.1.1.1"），None表示不使用multicast
            multicast_ttl: Multicast TTL值（默認1，僅本地網絡）
        """
        self.local_addr = (local_ip, local_port)
        self.server_addr = (server_ip, server_port)
        self.multicast_group = multicast_group
        self.multicast_ttl = multicast_ttl
        self.socket = None
        self.buffer = PacketBuffer(logger)
        self.logger = logger
    
    def open(self):
        """開啟UDP連接"""
        if self.socket:
            self.close()
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 設置 SO_REUSEPORT（允許多個進程綁定同一端口）
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                # Windows 或舊版 Linux 不支持
                pass
            
            # 如果是 multicast 接收者
            if self.multicast_group:
                # 設置 socket 選項
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # 綁定到端口（對於multicast，可以綁定到 0.0.0.0 或特定接口）
                self.socket.bind(('', self.local_addr[1]))
                
                # 加入 multicast 組
                multicast_addr = socket.inet_aton(self.multicast_group)
                interface = socket.inet_aton(self.local_addr[0] if self.local_addr[0] != '0.0.0.0' else '0.0.0.0')
                membership = struct.pack('4s4s', multicast_addr, interface)
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
                
                # 設置 multicast TTL（用於發送）
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.multicast_ttl)
                
                # 設置 multicast loopback（是否接收自己發送的數據）
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
                
                self.logger.info(f"開啟UDP Multicast連接: 組={self.multicast_group}, 端口={self.local_addr[1]}")
            else:
                # 普通 UDP 綁定
                self.socket.bind(self.local_addr)
                self.logger.info(f"開啟UDP連接: {self.local_addr[0]}:{self.local_addr[1]}")
        
            self.socket.settimeout(1.0)
            self.buffer.buffer.clear()
            return True
        except Exception as e:
            self.logger.error(f"開啟UDP連接失敗: {e}")
            return False
    
    def close(self):
        """關閉UDP連接"""
        if self.socket:
            # 如果是 multicast，離開組
            if self.multicast_group:
                try:
                    multicast_addr = socket.inet_aton(self.multicast_group)
                    interface = socket.inet_aton(self.local_addr[0] if self.local_addr[0] != '0.0.0.0' else '0.0.0.0')
                    membership = struct.pack('4s4s', multicast_addr, interface)
                    self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, membership)
                except Exception as e:
                    self.logger.warning(f"離開multicast組失敗: {e}")
            
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
    
    def send_data(self, data, addr: Optional[Tuple[str, int]] = None):
        """發送數據"""
        if not self.socket:
            self.logger.error("尚未開啟UDP連接")
            return False
        
        # 如果指定了地址，使用指定地址；否則使用 server_addr
        target_addr = addr if addr is not None else self.server_addr
        
        # 如果是 multicast，確保使用 multicast 地址
        if self.multicast_group and target_addr[0] != self.multicast_group:
            target_addr = (self.multicast_group, target_addr[1])
        
        try:
            self.socket.sendto(data, target_addr)
            return True
        except Exception as e:
            self.logger.error(f"發送數據失敗: {e}")
            return False
    
    def process_buffer(self, data):
        """處理緩衝區數據，返回完整封包列表"""
        return self.buffer.feed(data)


class PacketBuffer:
    """封包緩衝與切割（支持 DLE+STX/ACK）"""
    
    def __init__(self, logger):
        self.buffer = bytearray()
        self.logger = logger
    
    def feed(self, data):
        """喂入數據，返回完整封包列表"""
        self.buffer.extend(data)
        packets = []
        
        while len(self.buffer) >= 3:  # 最小封包（ACK = 9 bytes）
            result = self._find_packet_start()
            
            if result is None:
                if len(self.buffer) > 0:
                    self.logger.info(f"清空 {len(self.buffer)} bytes 無效數據")
                self.buffer.clear()
                break
            
            start_idx, packet_type = result
            
            if start_idx > 0:
                self.buffer = self.buffer[start_idx:]
            
            # 根據封包類型提取
            if packet_type == 'STX':
                if len(self.buffer) < 7:
                    break
                total = int.from_bytes(self.buffer[5:7], 'big')
            elif packet_type == 'ACK':
                total = 8  # DLE ACK SEQ ADDR(2) LEN(2) CKS
            else:
                total = 9  # NAK
            
            if len(self.buffer) < total:
                break  # 等待更多數據
            
            packet = bytes(self.buffer[:total])
            packets.append(packet)
           
            self.buffer = self.buffer[total:]
        
        return packets
    
    def _find_packet_start(self):
        """尋找封包開頭"""
        for i in range(len(self.buffer) - 1):
            if self.buffer[i] == 0xAA:  # DLE
                if self.buffer[i + 1] == 0xBB:  # STX
                    return (i, 'STX')
                elif self.buffer[i + 1] == 0xDD:  # ACK
                    return (i, 'ACK')
                elif self.buffer[i + 1] == 0xEE:  # NAK
                    return (i, 'NAK')
        return None