# core/frame.py
"""
幀編解碼
"""

import struct
from typing import Dict, Optional
from .utils import _u8, _u16, calculate_checksum
from config.constants import DLE, STX, ETX, ACK

class FrameDecoder:
    """幀解碼器"""
    
    @staticmethod
    def decode(frame: bytes) -> Dict:
        """解碼幀"""
        if not frame or len(frame) < 3:
            raise ValueError("幀長度不足")
        
        if frame[0] != DLE:
            raise ValueError("幀格式錯誤：缺少DLE")
        
        if frame[1] not in [STX, ACK]:
            raise ValueError("非ACK或STX幀")
        
        # 驗證校驗和
        if calculate_checksum(frame[:-1]) != frame[-1]:
            raise ValueError("校驗和錯誤")
        
        seq = frame[2]
        addr = int.from_bytes(frame[3:5], 'big')
        length = int.from_bytes(frame[5:7], 'big') if len(frame) > 6 else 0
        
        if frame[1] == STX:
            # STX幀：提取PAYLOAD字段（去除DLE+STX+SEQ+ADDR+LEN和DLE+ETX+CKS）
            payload = frame[7:-3] if len(frame) > 10 else b""
            return {
                "type": "STX",
                "seq": seq,
                "addr": addr,
                "len": length,
                "payload": payload
            }
        elif frame[1] == ACK:
            return {
                "type": "ACK",
                "seq": seq,
                "addr": addr,
                "len": length
            }
        else:
            raise ValueError(f"未知幀類型: {frame[1]:02X}")

class FrameEncoder:
    """幀編碼器"""
    
    @staticmethod
    def escape_dle(data: bytes) -> bytes:
        """DLE逸出處理：0xAA -> 0xAA 0xAA"""
        result = bytearray()
        for byte in data:
            result.append(byte)
            if byte == DLE:
                result.append(DLE)
        return bytes(result)
    
    @staticmethod
    def unescape_dle(data: bytes) -> bytes:
        """DLE反逸出處理：0xAA 0xAA -> 0xAA"""
        result = bytearray()
        i = 0
        while i < len(data):
            if data[i] == DLE and i + 1 < len(data) and data[i + 1] == DLE:
                result.append(DLE)
                i += 2
            else:
                result.append(data[i])
                i += 1
        return bytes(result)

class MessageFrame:
    """幀：DLE STX SEQ ADDR(2) LEN(2) INFO DLE ETX CKS"""
    
    @staticmethod
    def encode(seq: int, addr: int, info: bytes) -> bytes:
        """編碼幀"""
        # DLE逸出
        stuffed_info = FrameEncoder.escape_dle(info)
        
        # 計算長度：DLE(1) + STX(1) + SEQ(1) + ADDR(2) + LEN(2) + INFO + DLE(1) + ETX(1)
        length = 1 + 1 + 1 + 2 + 2 + len(stuffed_info) + 1 + 1
        
        # 構建幀頭
        header = struct.pack(">BBBHH", DLE, STX, _u8(seq), _u16(addr), _u16(length))
        
        # 構建幀尾
        tail = struct.pack(">BB", DLE, ETX)
        
        # 計算校驗和
        data_for_checksum = header + stuffed_info + tail
        
        # 組裝完整幀
        return header + stuffed_info + tail + struct.pack(">B", calculate_checksum(data_for_checksum))

class AckFrame:
    """ACK幀：DLE ACK SEQ ADDR(2) LEN(2) CKS"""
    
    @staticmethod
    def encode(seq: int, addr: int) -> bytes:
        """編碼ACK幀"""
        length = 8  # ACK幀固定長度
        addr_high = (addr >> 8) & 0xFF
        addr_low = addr & 0xFF
        
        header = struct.pack(">BBBHH", DLE, ACK, _u8(seq), _u16(addr), _u16(length))
        
        return header + struct.pack(">B", calculate_checksum(header))