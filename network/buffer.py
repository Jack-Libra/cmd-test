# network/buffer.py
"""
幀緩衝區管理
"""

import logging
from core.frame import FrameEncoder

class FrameBuffer:
    """幀緩衝與切割（支持 DLE+STX/ACK）"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.logger = logging.getLogger(__name__)
    
    def feed(self, data: bytes) -> list:
        """喂入數據，返回完整幀列表"""
        self.buffer.extend(data)
        frames = []
        
        while len(self.buffer) >= 3:  # 最小幀（ACK = 9 bytes）
            result = self._find_frame_start()
            
            if result is None:
                if len(self.buffer) > 0:
                    self.logger.debug(f"清空 {len(self.buffer)} bytes 無效數據")
                self.buffer.clear()
                break
            
            start_idx, frame_type = result
            
            if start_idx > 0:
                self.buffer = self.buffer[start_idx:]
            
            # 根據幀類型提取
            if frame_type == 'STX':
                if len(self.buffer) < 7:
                    break
                total = int.from_bytes(self.buffer[5:7], 'big')
            elif frame_type == 'ACK':
                total = 9  # DLE ACK SEQ ADDR(2) LEN(2) CKS
            else:
                total = 10  # NAK
            
            if len(self.buffer) < total:
                break  # 等待更多數據
            
            frame = bytes(self.buffer[:total])
            frames.append(frame)
            self.logger.debug(f"提取幀: {len(frame)} bytes (type={frame_type})")
            
            self.buffer = self.buffer[total:]
        
        return frames
    
    def _find_frame_start(self):
        """尋找幀開頭"""
        for i in range(len(self.buffer) - 1):
            if self.buffer[i] == 0xAA:  # DLE
                if self.buffer[i + 1] == 0xBB:  # STX
                    return (i, 'STX')
                elif self.buffer[i + 1] == 0xDD:  # ACK
                    return (i, 'ACK')
                elif self.buffer[i + 1] == 0xEE:  # NAK
                    return (i, 'NAK')
        return None