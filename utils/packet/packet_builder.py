import struct
from typing import Optional, Tuple
from utils.core import FRAME, stuff_info, _u8, _u16, xor_checksum, Ack, Nak
import logging

class PacketBuilder:
    """封包建構器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def build(self, cmd: str, params: list, seq: int = 1, addr: int = 0x0003) -> Tuple[bytes, str, Optional[bytes]]:
        """
        建立封包
        返回: (封包, 命令描述, 原始INFO bytes)
        """
        # 根據指令呼叫其餘函數建立 INFO
        info, cmd_desc = self._build_info(cmd, params, seq, addr)
        if info is None:
            self.logger.error(f"建立封包失敗: {cmd}")
            return bytes(), cmd_desc, None
        
        # 檢查 DLE 溢出處理
        stuffed_info = stuff_info(info)
        
        # 計算封包長度: DLE(1) + STX(1) + SEQ(1) + ADDR(2) + LEN(2) + INFO + DLE(1) + ETX(1) + CKS(1)
        length = 1 + 1 + 1 + 2 + 2 + len(stuffed_info) + 1 + 1
        
        # 建立封包開頭: DLE STX SEQ ADDR(2) LEN(2)
        header = struct.pack(">BBBHH", FRAME["DLE"], FRAME["STX"], _u8(seq), _u16(addr), _u16(length))
        
       
        # 封包結尾: DLE ETX
        tail = struct.pack(">BB", FRAME["DLE"], FRAME["ETX"])
        
        # 計算校驗和: 從開頭到結尾（不含CKS）
        data_for_checksum = header + stuffed_info + tail
        cks = xor_checksum(data_for_checksum)
        
        # 組裝完整封包
        packet = header + stuffed_info + tail + struct.pack(">B", cks)
        
        return packet, cmd_desc, info
    
    def _build_info(self, cmd: str, params: list, seq: int, addr: int) -> Tuple[Optional[bytes], str]:
        """
        根據指令建立 INFO 部分
        返回: (INFO bytes, 命令描述)
        """
        cmd = cmd.upper()
        
        if cmd == "5F10":
            return self._build_info_5f10(params, seq, addr)
        elif cmd == "5F40":
            return self._build_info_5f40(params, seq, addr)
        elif cmd == "5F48":
            return self._build_info_5f48(params, seq, addr)
        elif cmd == "5F1C":
            return self._build_info_5f1c(params, seq, addr)
        else:
            self.logger.error(f"不支援的命令: {cmd}")
            return None, ""
    
    def _build_info_5f10(self, params: list, seq: int, addr: int) -> Tuple[Optional[bytes], str]:
        """5F 10: 設定控制策略"""

        control = params[0] & 0xFF
        effect_time = params[1] & 0xFF
        
        info = struct.pack(">BBBB", 0x5F, 0x10, control, effect_time)
        cmd_desc = f"5F10 設定控制策略 (seq={seq}, addr=0x{addr:04X}, control=0x{control:02X}, time={effect_time}分)"
        
        return info, cmd_desc
    
    def _build_info_5f40(self, params: list, seq: int, addr: int) -> Tuple[Optional[bytes], str]:
        """5F 40: 查詢控制策略"""

        info = struct.pack(">BB", 0x5F, 0x40)
        cmd_desc = f"5F40 查詢控制策略 (seq={seq}, addr=0x{addr:04X})"
        
        return info, cmd_desc
    
    def _build_info_5f48(self, params: list, seq: int, addr: int) -> Tuple[Optional[bytes], str]:
        """5F 48: 查詢時制計畫"""

        info = struct.pack(">BB", 0x5F, 0x48)
        cmd_desc = f"5F48 查詢時制計畫 (seq={seq}, addr=0x{addr:04X})"
        
        return info, cmd_desc
    
    def _build_info_5f1c(self, params: list, seq: int, addr: int) -> Tuple[Optional[bytes], str]:
        """5F 1C: 設定時相或步階變換控制"""
        
        sub_phase_id = params[0] & 0xFF
        step_id = params[1] & 0xFF
        effect_time = params[2] & 0xFF
        
        info = struct.pack(">BBBBB", 0x5F, 0x1C, sub_phase_id, step_id, effect_time)
        cmd_desc = f"5F1C 設定時相或步階變換控制 (seq={seq}, addr=0x{addr:04X}, sub_phase={sub_phase_id}, step={step_id}, time={effect_time})"
        
        return info, cmd_desc
    