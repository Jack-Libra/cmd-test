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
