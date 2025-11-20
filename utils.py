"""
工具函數
"""
from config.constants import DLE, STX, ETX, ACK
from typing import Dict
import struct

# ============= DLE 處理函數 =============

def escape_dle(data: bytes) -> bytes:
    """DLE逸出處理：0xAA -> 0xAA 0xAA"""
    result = bytearray()
    for byte in data:
        result.append(byte)
        if byte == 0xAA:
            result.append(0xAA)
    return bytes(result)


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


def calculate_checksum(data: bytes) -> int:
    """計算XOR校驗和"""
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum & 0xFF


# ============= 封包解碼函數 =============

def decode(frame: bytes) -> Dict:
    """解碼封包"""
    if not frame or len(frame) < 3:
        raise ValueError("封包長度不足")
    
    if frame[0] != DLE:
        raise ValueError("封包格式錯誤：缺少DLE")
    
    if frame[1] not in [STX, ACK]:
        raise ValueError("非ACK或STX封包")
    
    # 驗證校驗和
    if calculate_checksum(frame[:-1]) != frame[-1]:
        raise ValueError("封包校驗和錯誤")
    
    seq = frame[2]
    addr = int.from_bytes(frame[3:5], 'big')
    length = int.from_bytes(frame[5:7], 'big') if len(frame) > 6 else 0
    
    if frame[1] == STX:
        # STX：提取PAYLOAD字段
        stuffed_payload = frame[7:-3] if len(frame) > 10 else b""
        
        # 處理DLE反溢出
        pair = bytes([0xAA, 0xAA])
        if pair in stuffed_payload:
            payload = unescape_dle(stuffed_payload)
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


# ============= 封包編碼函數 =============

def encode(seq: int, addr: int, payload: bytes = b"") -> bytes:
    """
    編碼封包（統一處理 ACK 和消息封包）
    
    Args:
        seq: 序列號
        addr: 地址
        payload: 負載數據，空字節表示 ACK 封包
        
    Returns:
        編碼後的封包字節
    """
    if payload:
        # 消息封包：DLE STX SEQ ADDR(2) LEN(2) INFO DLE ETX CKS
        payload_escaped = escape_dle(payload)
        length = 10 + len(payload_escaped)
        
        header = struct.pack(">BBBHH", DLE, STX, _u8(seq), _u16(addr), _u16(length))
        footer = struct.pack(">BB", DLE, ETX)
        data_for_checksum = header + payload_escaped + footer
        
        return header + payload_escaped + footer + struct.pack(">B", calculate_checksum(data_for_checksum))
    else:
        # ACK 封包：DLE ACK SEQ ADDR(2) LEN(2) CKS
        length = 8
        header = struct.pack(">BBBHH", DLE, ACK, _u8(seq), _u16(addr), _u16(length))
        
        return header + struct.pack(">B", calculate_checksum(header))

def int_to_binary_list(n: int) -> list:
    """將整數轉換為二進制列表（低位在前）"""
    if n == 0:
        return [0] * 8
    binary_str = format(n, '08b')
    reverse_str = binary_str[::-1]
    return [int(bit) for bit in reverse_str]
    
def binary_list_to_int(bits: list) -> int:
    """
    將二進制列表轉換為整數（高位在前）
    
    Args:
        bits: 二進制列表，如 [1,1,0,0,0,0,0,0]（高位在前）
              bits[0] 是 bit 7（最高位），bits[7] 是 bit 0（最低位）
    
    Returns:
        int: 轉換後的整數值
    
    Example:
        binary_list_to_int([1,1,0,0,0,0,0,0]) -> 0xC0 (192)
        binary_list_to_int([0,0,0,0,0,0,1,1]) -> 0x03 (3)
    """
    if len(bits) != 8:
        raise ValueError(f"二進制列表長度錯誤: 需要 8 個位，實際 {len(bits)} 個")
    
    if not all(bit in [0, 1] for bit in bits):
        raise ValueError(f"二進制列表格式錯誤: 只能包含 0 或 1")
    
    # 高位在前：bits[0] 是 bit 7，bits[i] 是 bit (7-i)
    return sum(bit << (7 - i) for i, bit in enumerate(bits))

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

def format_packet_display(packet, command, fields):
    """
    統一的封包顯示格式化函數
    
    Args:
        packet: 封包對象
        command: 指令碼
        fields: 字段映射字典 {顯示名稱: 值或獲取函數}
    
    Returns:
        格式化後的多行字符串
    """
    lines = []
    
    # 標題
    lines.append("="*60)
 
    lines.append(f"接收 {command} 封包: {packet.raw_packet}")
    lines.append("=== 封包詳細資訊 ===")
    
    # 標準字段
    lines.append(f"序列號 (SEQ): 0x{packet.seq:02X}")
    lines.append(f"控制器編號: TC{packet.tc_id:03d}")
    lines.append(f"指令: {command}")
    lines.append(f"訊息型態: {packet.reply_type}")
    
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
    lines.append(f"原始資料: {packet.raw_packet}")
    
    lines.append(f"接收時間: {packet.receive_time}")

    lines.append("="*60)
    
    return "\n".join(lines)    

def validate_param_range(value: int, field_name: str, 
                        min_val: int = 0, max_val: int = 0xFF) -> bool:
    """
    驗證參數範圍（通用工具函數）
    
    Args:
        value: 要驗證的值
        field_name: 字段名稱（用於錯誤提示）
        min_val: 最小值，默認 0
        max_val: 最大值，默認 0xFF
        
    Returns:
        是否在範圍內
        
    Raises:
        ValueError: 超出範圍
    """
    if not (min_val <= value <= max_val):
        raise ValueError(f"{field_name} 超出範圍 (0x{min_val:02X}~0x{max_val:02X}): {value}")
    return True
    
