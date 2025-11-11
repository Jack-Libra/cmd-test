# packet/parser/unified_field_parser.py

"""
統一字段解析器
處理所有類型的字段（靜態、動態、自定義、後處理）
"""

from typing import Dict, Any, List, Optional
from ..definitions.registry import DefinitionRegistry

class UnifiedFieldParser:
    """統一字段解析器"""
    
    def __init__(self, registry: DefinitionRegistry):
        self.registry = registry
    
    def parse_fields(self, payload: bytes, fields: List[Dict], result: Dict) -> Dict:
        """解析payload字段（統一處理）"""
        current_index = 0  # 當前 PAYLOAD 索引位置
        
        for field in fields:
            field_name = field["name"]
            field_type = field.get("type", "uint8")
            field_index = field.get("index")
            
            
            # 計算實際索引位置
            if field_index is None:
                actual_index = current_index
            else:
                # 固定索引
                actual_index = field_index
            
            # 解析字段值
            value = self._parse_field_by_type(payload, field, actual_index, result)
            
            if value is not None:
                # 應用映射（如果有）
                if "mapping" in field:
                    mapping = field["mapping"]
                    processed_value = mapping.get(value, f"未知(0x{value:02X})")
                else:
                    processed_value = value
                
                #應用後處理（如果有）
                if "post_process" in field:
                    result[field_name] = field["post_process"](processed_value, result)
                else:
                    result[field_name] = processed_value
            else:
                result[field_name] = None
            
            # 更新當前索引（用於下一個字段）
            if field_index != "dynamic" and field_index is not None:
                current_index = self._calculate_next_index(
                    actual_index, field_type, field, value, result
                )
        
        return result
    
    def _parse_field_by_type(self, payload: bytes, field: Dict, 
                            index: int, result: Dict) -> Any:
        """根據字段類型解析"""
        field_type = field["type"]
        
        if field_type == "uint8":
            return self._parse_uint8(payload, index)
        elif field_type == "uint16":
            endian = field.get("endian", "big")
            return self._parse_uint16(payload, index, endian)
        elif field_type == "list":
            return self._parse_list(payload, field, index, result)
        elif field_type == "struct_list":
            return self._parse_struct_list(payload, field, index, result)
        else:
            return None
    
    def _parse_uint8(self, payload: bytes, index: int) -> Optional[int]:
        """解析 uint8"""
        if index >= len(payload):
            return None
        return payload[index]
    
    def _parse_uint16(self, payload: bytes, index: int, endian: str = "big") -> Optional[int]:
        """解析 uint16"""
        if index + 1 >= len(payload):
            return None
        return int.from_bytes(payload[index:index+2], endian)
    
    def _parse_list(self, payload: bytes, field: Dict, index: int, result: Dict) -> List:
        """解析列表字段"""
        count = result.get(field.get("count_from", ""), 0)
        item_type = field.get("item_type", "uint8")
        items = []
        
        type_def = self.registry.get_field_type(item_type)
        if not type_def:
            return items
        
        item_size = type_def["size"]
        for i in range(count):
            item_index = index + i * item_size
            if item_index + item_size <= len(payload):
                if item_type == "uint16":
                    endian = field.get("endian", "big")
                    items.append(self._parse_uint16(payload, item_index, endian))
                else:
                    items.append(self._parse_uint8(payload, item_index))
        
        return items
    
    def _parse_struct_list(self, payload: bytes, field: Dict, index: int, result: Dict) -> List:
        """解析結構體列表字段"""
        count = result.get(field.get("count_from", ""), 0)
        item_fields = field.get("item_fields", [])
        items = []
        
        current_index = index
        for i in range(count):
            item = {}
            for item_field in item_fields:
                field_type = item_field["type"]
                field_name = item_field["name"]
                
                if field_type == "uint8":
                    value = self._parse_uint8(payload, current_index)
                    current_index += 1
                elif field_type == "uint16":
                    endian = item_field.get("endian", "big")
                    value = self._parse_uint16(payload, current_index, endian)
                    current_index += 2
                else:
                    value = None
                
                item[field_name] = value if value is not None else 0
            
            items.append(item)
        
        return items
    
    
    def _calculate_next_index(self, current_index: int, field_type: str, 
                             field: Dict, value: Any, result: Dict) -> int:
        """計算下一個字段的索引位置"""
        if field_type == "uint8":
            return current_index + 1
        elif field_type == "uint16":
            return current_index + 2
        elif field_type == "list":
            count = result.get(field.get("count_from", ""), 0)
            item_type = field.get("item_type", "uint8")
            item_size = 1 if item_type == "uint8" else 2
            return current_index + count * item_size
        elif field_type == "struct_list":
            count = result.get(field.get("count_from", ""), 0)
            item_fields = field.get("item_fields", [])
            item_size = sum(1 if f["type"] == "uint8" else 2 for f in item_fields)
            return current_index + count * item_size
        else:
            return current_index + 1

