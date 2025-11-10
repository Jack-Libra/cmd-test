# core/utils.py
"""
工具函數
"""

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

def calculate_checksum(data: bytes) -> int:
    """計算XOR校驗和"""
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum & 0xFF