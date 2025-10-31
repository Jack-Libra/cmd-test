import logging

import logging

class FrameBuffer:
    """封包緩衝與切割（支援 DLE+STX/ACK）"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.logger = logging.getLogger(__name__)
    
    def feed(self, data: bytes):
        """餵入資料，返回完整封包列表"""
        self.buffer.extend(data)
        packets = []
        
        while len(self.buffer) >= 3:  # 最小封包（ACK = 9 bytes）
            # 尋找封包開頭並確認類型
            result = self._find_frame_start()
            
            if result is None:
                if len(self.buffer) > 0:
                    self.logger.debug(f"清空 {len(self.buffer)} bytes 無效資料（未找到有效封包開頭）")
                self.buffer.clear()
                break
            
            start_idx, frame_type = result
            
            if start_idx > 0:
                self.buffer = self.buffer[start_idx:]
            
            
            # 根據已確認的封包類型提取
            if frame_type == 'STX':  
                # 直接讀取 LEN 欄位（第 6、7 bytes，索引 5、6）
                if len(self.buffer) < 7:
                    self.logger.debug(f"STX資料錯誤: {len(self.buffer)} < 7")
                    break 
                
                total = int.from_bytes(self.buffer[5:7], 'big')
            
            elif frame_type == 'ACK':
                
                total = 9  # DLE ACK SEQ ADDR(2) LEN(2) CKS
            
            else: # NAK
                total = 10  # DLE NAK SEQ ADDR(2) LEN(2) ERR CKS

            
            if len(self.buffer) < total:
                self.logger.debug(f"資料bytes計算錯誤: {len(self.buffer)} < {total}")
                break  # 等待更多資料
            
            packet = bytes(self.buffer[:total])
            packets.append(packet)
            self.logger.debug(f"提取封包: {len(packet)} bytes (type={frame_type})")
            
            self.buffer = self.buffer[total:]
        
        return packets
    
    def _find_frame_start(self):
        """
        尋找有效的封包開頭並確認封包類型
        
        返回: (start_index, frame_type) 或 None
        """
        # 控制碼到類型的映射
        CTRL_TO_TYPE = {
            0xBB: 'STX',
            0xDD: 'ACK',
            0xEE: 'NAK'
        }
        
        i = 0
        while i < len(self.buffer) - 1:
            if self.buffer[i] == 0xAA:
                ctrl = self.buffer[i + 1]
                
                if ctrl in CTRL_TO_TYPE:
                    # 找到有效封包開頭，同時確認類型
                    return (i, CTRL_TO_TYPE[ctrl])
                
                elif ctrl == 0xAA:
                    # INFO 中的轉義 DLE，跳過
                    i += 1
                    continue
                
                # 無效的控制碼，跳過
                i += 1
            else:
                i += 1
        
        return None
        