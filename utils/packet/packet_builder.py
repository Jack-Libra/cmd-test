import struct
from utils.core import MessageFrame, Ack, Nak

class PacketBuilder:
    """封包建構器"""
    
    # ===== 號控 群組 =====
    @staticmethod
    def build_5f10(seq: int, addr: int, control: int, effect_time: int) -> bytes:
        """5F 10: 設定控制策略"""
        info = struct.pack(">BBBB", 0x5F, 0x10, control & 0xFF, effect_time & 0xFF)
        return MessageFrame.encode(seq, addr, info)
    
    @staticmethod
    def build_5f40(seq: int, addr: int) -> bytes:
        """5F 40: 查詢控制策略"""
        info = struct.pack(">BB", 0x5F, 0x40)
        return MessageFrame.encode(seq, addr, info)
    
    @staticmethod
    def build_5f48(seq: int, addr: int) -> bytes:
        """5F 48: 查詢時制計畫"""
        info = struct.pack(">BB", 0x5F, 0x48)
        return MessageFrame.encode(seq, addr, info)
    
    @staticmethod
    def build_5f1c(seq: int, addr: int, sub_phase_id: int, step_id: int, effect_time: int) -> bytes:
        """5F 1C: 設定時相或步階變換控制"""
        info = struct.pack(">BBBBB", 0x5F, 0x1C, sub_phase_id & 0xFF, step_id & 0xFF, effect_time & 0xFF)
        return MessageFrame.encode(seq, addr, info)
        
    # ===== ACK/NAK =====
    @staticmethod
    def build_ack(seq: int, addr: int) -> bytes:
        """建構 ACK"""
        return Ack.encode(seq, addr)
    
    @staticmethod
    def build_nak(seq: int, addr: int, err: int) -> bytes:
        """建構 NAK"""
        return Nak.encode(seq, addr, err)