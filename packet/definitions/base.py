"""
基礎定義和類型系統
"""

# 字段類型定義
FIELD_TYPES = {
    "uint8": {
        "size": 1,
        "parser": lambda data, offset: data[offset] if offset < len(data) else 0,
        "builder": lambda value: bytes([value & 0xFF])
    },
    "uint16": {
        "size": 2,
        "parser": lambda data, offset, endian="big": (
            int.from_bytes(data[offset:offset+2], endian) 
            if offset + 1 < len(data) else 0
        ),
        "builder": lambda value, endian="big": (value & 0xFFFF).to_bytes(2, endian)
    },
    "bytes": {
        "size": None,  # 動態大小
        "parser": lambda data, offset, length: data[offset:offset+length] if offset + length <= len(data) else b"",
        "builder": lambda value: value if isinstance(value, bytes) else bytes(value)
    }
}

# 驗證器類型
VALIDATORS = {
    "min_length": lambda data, length: len(data) >= length,
    "exact_length": lambda data, length: len(data) == length,
    "max_length": lambda data, length: len(data) <= length,
    "custom": lambda data, func: func(data) if func else True
}

