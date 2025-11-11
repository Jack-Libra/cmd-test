"""
定義註冊表
"""

from typing import Dict, Optional
from .group_5f import F5_GROUP_DEFINITIONS
from .group_0f import F0_GROUP_DEFINITIONS

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


class DefinitionRegistry:
    """定義註冊表"""
    
    def __init__(self):
        self.definitions = {
            **F5_GROUP_DEFINITIONS,
            **F0_GROUP_DEFINITIONS
        }
        self.field_types = FIELD_TYPES
        self.validators = VALIDATORS
    
    def get_definition(self, cmd_code: str) -> Optional[Dict]:
        """獲取封包定義"""
        return self.definitions.get(cmd_code)
    
    def register_definition(self, cmd_code: str, definition: Dict):
        """註冊新封包定義"""
        self.definitions[cmd_code] = definition
    
    def get_field_type(self, field_type: str) -> Optional[Dict]:
        """獲取字段類型定義"""
        return self.field_types.get(field_type)
    
    def get_validator(self, validator_type: str):
        """獲取驗證器"""
        return self.validators.get(validator_type)



