# config/network.py
"""
UDP傳輸層
"""

import socket
import logging


class UDPTransport:
    """UDP傳輸層"""
    
    def __init__(self, local_ip, local_port, 
                 server_ip, server_port):
        self.local_addr = (local_ip, local_port)
        self.server_addr = (server_ip, server_port)
        self.socket = None
        self.buffer = PacketBuffer()
        self.logger = logging.getLogger(__name__)
    
    def open(self):
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
    
    def send_data(self, data, addr):
        """發送數據"""
        if not self.socket:
            self.logger.error("尚未開啟UDP連接")
            return False
        target_addr = addr if addr is not None else self.server_addr
        try:
            self.socket.sendto(data, target_addr)
            self.logger.info(f"發送數據到 {target_addr[0]}:{target_addr[1]}")
            return True
        except Exception as e:
            self.logger.error(f"發送數據失敗: {e}")
            return False
    
    def process_buffer(self, data):
        """處理緩衝區數據，返回完整封包列表"""
        return self.buffer.feed(data)


class PacketBuffer:
    """封包緩衝與切割（支持 DLE+STX/ACK）"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.logger = logging.getLogger(__name__)
    
    def feed(self, data):
        """喂入數據，返回完整封包列表"""
        self.buffer.extend(data)
        packets = []
        
        while len(self.buffer) >= 3:  # 最小封包（ACK = 9 bytes）
            result = self._find_packet_start()
            
            if result is None:
                if len(self.buffer) > 0:
                    self.logger.debug(f"清空 {len(self.buffer)} bytes 無效數據")
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
                total = 9  # DLE ACK SEQ ADDR(2) LEN(2) CKS
            else:
                total = 10  # NAK
            
            if len(self.buffer) < total:
                break  # 等待更多數據
            
            packet = bytes(self.buffer[:total])
            packets.append(packet)
            self.logger.debug(f"提取封包: {len(packet)} bytes (type={packet_type})")
            
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