"""
封包構建器

負責構建封包，並返回構建結果
"""

import logging
from utils import MessageFrame
from packet.packet_definition import PacketDefinition


class PacketBuilder:
    """封包構建器"""
    
    def __init__(self, packet_def):
        self.logger = logging.getLogger(__name__)
        self.packet_def = PacketDefinition()
        self.sub_builder = SubBuilder(packet_def=self.packet_def)
    
    def build(self, cmd_code, fields, seq=1, addr=0):
        """構建封包"""
        try:
            definition = self.packet_def.get_definition(cmd_code=cmd_code)
            if not definition:
                self.logger.error(f"未找到封包定義: {cmd_code}")
                return None
            
            # 構建PAYLOAD字段
            payload = self._build_payload(definition, fields)
            if payload is None:
                return None
            
            # 構建完整封包
            packet = MessageFrame.encode(seq, addr, payload)
            return packet
            
        except Exception as e:
            self.logger.error(f"構建封包失敗: {e}", exc_info=True)
            return None
    
    def _build_payload(self, definition, fields):
        """構建PAYLOAD字段"""
        payload = bytearray()
        
        # 添加群組碼和命令碼
        group = definition.get("group")
        command = definition.get("command")
        
        if group == "5F":
            payload.append(0x5F)
        elif group == "0F":
            payload.append(0x0F)
        else:
            self.logger.error(f"未知群组: {group}")
            return None
        
        payload.append(command)
        
        # 構建靜態字段
        if "fields" in definition:
            field_data = self.sub_builder.build_fields(fields=definition["fields"], data=fields)
            payload.extend(field_data)
        
        # 構建動態字段
        if "dynamic_fields" in definition:
            dynamic_data = self.sub_builder.build_dynamic_fields(
                dynamic_fields=definition["dynamic_fields"], data=fields
            )
            payload.extend(dynamic_data)
        
        return bytes(payload)


class SubBuilder:
    """子構建器"""
    
    def __init__(self, packet_def):
        self.packet_def = packet_def
    
    def build_fields(self, fields, data):
        """構建子字段數據"""
        result = bytearray()
        
        # 先構建固定字段
        for field in fields:
            field_name = field["name"]
            field_type = field["type"]
            
            if field_name in data:
                value = data[field_name]
                type_def = self.packet_def.get_field_type(field_type=field_type)
                
                if type_def:
                    builder = type_def["builder"]
                    if field_type == "uint16":
                        endian = field.get("endian", "big")
                        result.extend(builder(value, endian))
                    else:
                        result.extend(builder(value))
        
        return bytes(result)
    
    def build_dynamic_fields(self, dynamic_fields, data):
        """構建子動態字段數據"""
        result = bytearray()
        
        for field_name, field_def in dynamic_fields.items():
            if field_name not in data:
                continue
            
            value = data[field_name]
            field_type = field_def["type"]
            
            if field_type == "list":
                # 列表類型
                item_type = field_def.get("item_type", "uint8")
                type_def = self.packet_def.get_field_type(field_type=item_type)
                
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
                                type_def = self.packet_def.get_field_type(field_type=field_type_in_item)
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
                type_def = self.packet_def.get_field_type(field_type=field_type)
                if type_def:
                    builder = type_def["builder"]
                    if field_type == "uint16":
                        endian = field_def.get("endian", "big")
                        result.extend(builder(value, endian))
                    else:
                        result.extend(builder(value))
        
        return bytes(result)
