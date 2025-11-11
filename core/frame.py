# core/frame.py
"""
封包通用處理類

處裡header、footer的編解碼、校驗和的計算、DLE(反)逸出處理

"""

import struct
from typing import Dict, Optional
from .utils import _u8, _u16
from config.constants import DLE, STX, ETX, ACK

class BaseCoder:
    """封包通用處理類"""
    
    @staticmethod
    def escape_dle(data: bytes) -> bytes:
        """DLE逸出處理：0xAA -> 0xAA 0xAA"""
        result = bytearray()
        for byte in data:
            result.append(byte)
            if byte == 0xAA:
                result.append(0xAA)
        return bytes(result)
    
    @staticmethod
    def unescape_dle(data: bytes) -> bytes:
        """DLE反逸出處理：0xAA 0xAA -> 0xAA"""
        result = bytearray()
        i = 0
        while i < len(data):
            if data[i] == 0xAA and i + 1 < len(data) and data[i + 1] == 0xAA:
                result.append(0xAA)
                i += 2
            else:
                result.append(data[i])
                i += 1
        return bytes(result)
    
    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """計算XOR校驗和"""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum & 0xFF



class FrameDecoder:
    """封包通用解碼器"""
    
    @staticmethod
    def decode(frame: bytes) -> Dict:
        """解碼幀"""
        if not frame or len(frame) < 3:
            raise ValueError("封包長度不足")
        
        if frame[0] != DLE:
            raise ValueError("封包格式錯誤：缺少DLE")
        
        if frame[1] not in [STX, ACK]:
            raise ValueError("非ACK或STX封包")
        
        # 驗證校驗和
        if BaseCoder.calculate_checksum(frame[:-1]) != frame[-1]:
            raise ValueError("封包校驗和錯誤")
        
        seq = frame[2]
        addr = int.from_bytes(frame[3:5], 'big')
        length = int.from_bytes(frame[5:7], 'big') if len(frame) > 6 else 0
        
        if frame[1] == STX:
            # STX：提取PAYLOAD字段（去除DLE+STX+SEQ+ADDR+LEN和DLE+ETX+CKS）
            stuffed_payload = frame[7:-3] if len(frame) > 10 else b""
            
            # 在解析前檢查並處理DLE反溢出（如果包含轉義的DLE：0xAA 0xAA）
            pair = bytes([0xAA, 0xAA])
            if pair in stuffed_payload:
                payload = BaseCoder.unescape_dle(stuffed_payload)
            else:
                payload = stuffed_payload
                     
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
            raise ValueError(f"未知封包類型: {frame[1]:02X}")


class MessageFrame:
    """幀：DLE STX SEQ ADDR(2) LEN(2) INFO DLE ETX CKS"""
    
    @staticmethod
    def encode(seq: int, addr: int, info: bytes) -> bytes:
        """編碼幀"""
        # DLE逸出
        payload = BaseCoder.escape_dle(info)
        
        # 計算長度：DLE(1) + STX(1) + SEQ(1) + ADDR(2) + LEN(2) + INFO + DLE(1) + ETX(1) + CKS(1)
        length = 10 + len(payload)
        
        # 構建幀頭
        header = struct.pack(">BBBHH", DLE, STX, _u8(seq), _u16(addr), _u16(length))
        
        # 構建幀尾
        footer = struct.pack(">BB", DLE, ETX)
        
        # 計算校驗和
        data_for_checksum = header + payload + footer
        
        # 組裝完整幀
        return header + payload + footer + struct.pack(">B", BaseCoder.calculate_checksum(data_for_checksum))

class AckFrame:
    """ACK封包：DLE ACK SEQ ADDR(2) LEN(2) CKS"""
    
    @staticmethod
    def encode(seq: int, addr: int) -> bytes:
        """編碼ACK封包"""
        length = 8  # ACK封包固定長度
        addr_high = (addr >> 8) & 0xFF
        addr_low = addr & 0xFF
        
        header = struct.pack(">BBBHH", DLE, ACK, _u8(seq), _u16(addr), _u16(length))
        
        return header + struct.pack(">B", BaseCoder.calculate_checksum(header))