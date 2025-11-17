"""
封包定義

負責定義封包的格式和解析方式
"""

from typing import Dict
from packet.definitions.group_5f import F5_GROUP_DEFINITIONS
from packet.definitions.group_0f import F0_GROUP_DEFINITIONS
from utils import binary_list_to_int
# 字段類型定義
FIELD_TYPES = {
    "uint8": {
        "size": 1,
        # 從字節數據解析（接收封包時使用）
        "parser": lambda data, offset: data[offset] if offset < len(data) else 0,
        # 構建為字節（發送封包時使用）
        "builder": lambda value: bytes([value & 0xFF]),
        # 從用戶輸入字符串解析（命令行輸入時使用）
        "input_parsers": {
            "dec": lambda value_str, param_name: (
                int(value_str, 10) if value_str.isdigit() 
                else _raise_value_error(param_name, value_str, "十進制數字")
            ),
            "hex": lambda value_str, param_name: (
                int(value_str[2:] if value_str.startswith(('0x', '0X')) else value_str, 16)
                if all(c in '0123456789ABCDEFabcdef' for c in (value_str[2:] if value_str.startswith(('0x', '0X')) else value_str))
                else _raise_value_error(param_name, value_str, "十六進制")
            ),
            "binary": lambda value_str, param_name: (
                binary_list_to_int([int(bit) for bit in value_str.strip()])
                if all(c in '01' for c in value_str.strip()) and len(value_str.strip()) == 8
                else _raise_value_error(param_name, value_str, "8位二進制字符串，如 10101010")
            )
        }
    },
    "uint16": {
        "size": 2,
        "parser": lambda data, offset, endian="big": (
            int.from_bytes(data[offset:offset+2], endian) 
            if offset + 1 < len(data) else 0
        ),
        "builder": lambda value, endian="big": (value & 0xFFFF).to_bytes(2, endian),
        "input_parsers": {
            "dec": lambda value_str, param_name: (
                int(value_str, 10) if value_str.isdigit() 
                else _raise_value_error(param_name, value_str, "十進制數字")
            ),
            "hex": lambda value_str, param_name: (
                int(value_str[2:] if value_str.startswith(('0x', '0X')) else value_str, 16)
                if all(c in '0123456789ABCDEFabcdef' for c in (value_str[2:] if value_str.startswith(('0x', '0X')) else value_str))
                else _raise_value_error(param_name, value_str, "十六進制")
            ),
            "binary": lambda value_str, param_name: (
                # uint16 的二进制输入可以支持16位
                int(value_str.strip(), 2)
                if all(c in '01' for c in value_str.strip()) and len(value_str.strip()) <= 16
                else _raise_value_error(param_name, value_str, "16位二進制字符串")
            )
        }
    },
    "bytes": {
        "size": None,
        "parser": lambda data, offset, length: data[offset:offset+length] if offset + length <= len(data) else b"",
        "builder": lambda value: value if isinstance(value, bytes) else bytes(value)
    }
}
def _raise_value_error(param_name, value_str, expected_format):
    """輔助函數：拋出格式錯誤"""
    raise ValueError(f"{param_name} 格式錯誤: {value_str} (應為{expected_format})")


class PacketDefinition:
    """封包定義"""
    
    def __init__(self):
        self.definitions = {
            **F5_GROUP_DEFINITIONS,
            **F0_GROUP_DEFINITIONS
        }
        self.field_types = FIELD_TYPES
    
    def get_definition(self, cmd_code):
        """獲取封包定義"""
        return self.definitions.get(cmd_code)
      
    
    def get_field_type(self, field_type):
        """獲取字段類型定義"""
        return self.field_types.get(field_type)

    def get_field_definition(self, definition, field_name):
        """從指令定義中獲取指定字段的定義"""
        for field in definition.get("fields", []):
            if field.get("name") == field_name:
                return field
        return None       

    def parse_input(self, value_str: str, field_def: Dict, param_name: str = None) -> int:
        """
        從用戶輸入字符串解析參數值
        
        Args:
            value_str: 參數字符串
            field_def: 字段定義字典
            param_name: 參數名稱（用於錯誤提示），如果為None則從field_def獲取
            
        Returns:
            解析後的數值
            
        Raises:
            ValueError: 解析失敗
        """
        if param_name is None:
            param_name = field_def.get("name", "參數")
        
        field_type = field_def.get("type", "uint8")
        input_type = field_def.get("input_type", "dec")
        
        # 獲取字段類型定義
        type_def = self.get_field_type(field_type)
        if not type_def:
            raise ValueError(f"未知的字段類型: {field_type}")
        
        # 獲取輸入解析器
        input_parsers = type_def.get("input_parsers", {})
        if not input_parsers:
            raise ValueError(f"字段類型 {field_type} 不支援輸入解析")
        
        parser = input_parsers.get(input_type)
        if not parser:
            raise ValueError(f"字段類型 {field_type} 不支援輸入格式: {input_type}")
        
        # 執行解析
        try:
            return parser(value_str, param_name)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"{param_name} 解析失敗: {e}")    



