# network/buffer.py
"""
封包緩衝區管理
"""

import logging

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