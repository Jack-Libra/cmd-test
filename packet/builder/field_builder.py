"""
字段構建器
"""

from typing import Dict, Any, List
from ..definitions.registry import DefinitionRegistry

class FieldBuilder:
    """字段構建器"""
    
    def __init__(self, registry: DefinitionRegistry):
        self.registry = registry
    
    def build_fields(self, fields: List[Dict], data: Dict) -> bytes:
        """構建字段數據"""
        result = bytearray()
        
        # 先構建固定字段
        for field in fields:
            field_name = field["name"]
            field_type = field["type"]
            
            if field_name in data:
                value = data[field_name]
                type_def = self.registry.get_field_type(field_type)
                
                if type_def:
                    builder = type_def["builder"]
                    if field_type == "uint16":
                        endian = field.get("endian", "big")
                        result.extend(builder(value, endian))
                    else:
                        result.extend(builder(value))
        
        return bytes(result)
    
    def build_dynamic_fields(self, dynamic_fields: Dict, data: Dict) -> bytes:
        """構建動態字段數據"""
        result = bytearray()
        
        for field_name, field_def in dynamic_fields.items():
            if field_name not in data:
                continue
            
            value = data[field_name]
            field_type = field_def["type"]
            
            if field_type == "list":
                # 列表類型
                item_type = field_def.get("item_type", "uint8")
                type_def = self.registry.get_field_type(item_type)
                
                if type_def and isinstance(value, list):
                    builder = type_def["builder"]
                    for item in value:
                        if item_type == "uint16":
                            endian = field_def.get("endian", "big")
                            result.extend(builder(item, endian))
                        else:
                            result.extend(builder(item))
            
            elif field_type == "struct_list":
                # 結構體列表類型
                item_fields = field_def.get("item_fields", [])
                if isinstance(value, list):
                    for item in value:
                        for field in item_fields:
                            field_name_in_item = field["name"]
                            field_type_in_item = field["type"]
                            
                            if field_name_in_item in item:
                                type_def = self.registry.get_field_type(field_type_in_item)
                                if type_def:
                                    builder = type_def["builder"]
                                    item_value = item[field_name_in_item]
                                    if field_type_in_item == "uint16":
                                        endian = field.get("endian", "big")
                                        result.extend(builder(item_value, endian))
                                    else:
                                        result.extend(builder(item_value))
            
            else:
                # 單個字段
                type_def = self.registry.get_field_type(field_type)
                if type_def:
                    builder = type_def["builder"]
                    if field_type == "uint16":
                        endian = field_def.get("endian", "big")
                        result.extend(builder(value, endian))
                    else:
                        result.extend(builder(value))
        
        return bytes(result)

