# core/utils.py
"""
工具函數
"""
from config.constants import DLE, STX, ETX, ACK
from typing import Dict
import struct

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
        """解碼封包"""
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
    """封包：DLE STX SEQ ADDR(2) LEN(2) INFO DLE ETX CKS"""
    
    @staticmethod
    def encode(seq: int, addr: int, info: bytes) -> bytes:
        """編碼封包"""
        # DLE逸出
        payload = BaseCoder.escape_dle(info)
        
        # 計算長度：DLE(1) + STX(1) + SEQ(1) + ADDR(2) + LEN(2) + INFO + DLE(1) + ETX(1) + CKS(1)
        length = 10 + len(payload)
        
        # 構建封包頭
        header = struct.pack(">BBBHH", DLE, STX, _u8(seq), _u16(addr), _u16(length))
        
        # 構建封包尾
        footer = struct.pack(">BB", DLE, ETX)
        
        # 計算校驗和
        data_for_checksum = header + payload + footer
        
        # 組裝完整封包
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


def int_to_binary_list(n: int) -> list:
    """將整數轉換為二進制列表（低位在前）"""
    if n == 0:
        return [0] * 8
    binary_str = format(n, '08b')
    reverse_str = binary_str[::-1]
    return [int(bit) for bit in reverse_str]

def _u8(x: int) -> int:
    """確保值在uint8範圍內"""
    if not (0 <= x <= 0xFF):
        raise ValueError(f"u8 range error: {x}")
    return x

def _u16(x: int) -> int:
    """確保值在uint16範圍內"""
    if not (0 <= x <= 0xFFFF):
        raise ValueError(f"u16 range error: {x}")
    return x

def format_packet_display(packet: dict, command: str, 
                         fields: dict) -> str:
    """
    統一的封包顯示格式化函數
    
    Args:
        packet: 解析後的封包字典
        command: 指令碼
        fields: 字段映射字典 {顯示名稱: 值或獲取函數}
    
    Returns:
        格式化後的多行字符串
    """
    lines = []
    
    # 標題
    lines.append("="*60)
    raw_packet = packet.get("原始封包")
    lines.append(f"接收 {command} 封包: {raw_packet}")
    lines.append("=== 封包詳細資訊 ===")
    
    # 標準字段
    lines.append(f"序列號 (SEQ): 0x{packet.get('序列號', 0):02X}")
    lines.append(f"控制器編號: TC{packet.get('號誌控制器ID', 0):03d}")
    lines.append(f"指令: {command}")
    
    # 自定義字段
    for label, value in fields.items():
        if callable(value):
            value = value(packet)
        
        if isinstance(value, list):
            for item in value:
                lines.append(str(item))
        else:
            lines.append(f"{label}: {value}")
    
    # 結尾
    lines.append(f"原始資料: {raw_packet}")
    
    receive_time = packet.get("接收時間")
    lines.append(f"接收時間: {receive_time}")

    lines.append("="*60)
    
    return "\n".join(lines)    
