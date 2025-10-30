import logging

class FrameBuffer:
    """封包緩衝與切割（DLE+STX ... DLE+ETX+CKS）"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.logger = logging.getLogger(__name__)
    
    def feed(self, data: bytes) -> list[bytes]:
        """餵入資料，返回完整封包列表"""
        self.buffer.extend(data)
        packets = []
        
        while len(self.buffer) >= 10:  # 最小封包長度
            # 尋找 DLE(0xAA) + STX(0xBB)
            start_idx = self._find_start()
            
            if start_idx == -1:
                # 沒找到開頭，清空緩衝區
                if len(self.buffer) > 0:
                    self.logger.warning(f"清空 {len(self.buffer)} bytes 無效資料")
                self.buffer.clear()
                break
            
            # 捨棄開頭前的無效資料
            if start_idx > 0:
                self.logger.warning(f"捨棄 {start_idx} bytes 無效資料")
                self.buffer = self.buffer[start_idx:]
            
            # 檢查長度欄位
            if len(self.buffer) < 7:
                break  # 資料不足，等待更多
            
            # 讀取 LEN 欄位 (offset 5~6, big-endian)
            length = int.from_bytes(self.buffer[5:7], 'big')
            total = length + 1  # +1 for CKS
            
            if len(self.buffer) < total:
                break  # 等待更多資料
            
            # 提取完整封包
            packet = bytes(self.buffer[:total])
            
            # 驗證尾端 DLE(0xAA) + ETX(0xCC)
            if self._validate_tail(packet):
                packets.append(packet)
                self.logger.debug(f"提取封包: {len(packet)} bytes")
            else:
                self.logger.warning("封包尾端格式錯誤，跳過")
            
            # 移除已處理的封包
            self.buffer = self.buffer[total:]
        
        return packets
    
    def _find_start(self) -> int:
        """尋找 DLE(0xAA) + STX(0xBB) 開頭"""
        for i in range(len(self.buffer) - 1):
            if self.buffer[i] == 0xAA and self.buffer[i+1] == 0xBB:
                return i
        return -1
    
    def _validate_tail(self, packet: bytes) -> bool:
        """驗證 DLE(0xAA) + ETX(0xCC) 尾端"""
        return len(packet) >= 3 and packet[-3] == 0xAA and packet[-2] == 0xCC
    
    def clear(self):
        """清空緩衝區"""
        self.buffer.clear()        