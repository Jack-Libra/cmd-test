"""
封包構建器

負責構建封包，並返回構建結果
"""

import logging
from typing import Dict, Any, Optional, Protocol
from utils import MessageFrame


# ============= Protocol 接口 =============

class PacketDefinitionProtocol(Protocol):
    """封包定義協議接口"""
    def get_definition(self, cmd_code: str) -> Optional[Dict[str, Any]]: ...
    def get_field_type(self, field_type: str) -> Optional[Dict[str, Any]]: ...


# ============= 字段構建器 =============

class FieldBuilder:
    """字段構建器 - 專門處理字段到字節的轉換"""
    
    def __init__(self, packet_def: PacketDefinitionProtocol):
        self.packet_def = packet_def
    
    def build_field(self, field: Dict[str, Any], value: Any) -> bytes:
        """構建單個字段為字節"""
        field_type = field.get("type", "uint8")
        
        if field_type == "list":
            return self._build_list(field, value)
        elif field_type == "uint16":
            endian = field.get("endian", "big")
            return self._build_uint16(value, endian)
        else:
            return self._build_uint8(value)
    
    def _build_uint8(self, value: int) -> bytes:
        """構建 uint8"""
        type_def = self.packet_def.get_field_type("uint8")
        if type_def:
            return type_def["builder"](value)
        return bytes([value & 0xFF])
    
    def _build_uint16(self, value: int, endian: str = "big") -> bytes:
        """構建 uint16"""
        type_def = self.packet_def.get_field_type("uint16")
        if type_def:
            return type_def["builder"](value, endian)
        return (value & 0xFFFF).to_bytes(2, endian)
    
    def _build_list(self, field: Dict[str, Any], value: Any) -> bytes:
        """構建列表"""
        if not isinstance(value, list):
            return b""
        
        result = bytearray()
        item_type = field.get("item_type", "uint8")
        
        for item in value:
            if item_type == "uint16":
                endian = field.get("endian", "big")
                result.extend(self._build_uint16(item, endian))
            else:
                result.extend(self._build_uint8(item))
        
        return bytes(result)


# ============= 封包構建器 =============

class PacketBuilder:
    """封包構建器"""
    
    def __init__(self, packet_def: PacketDefinitionProtocol):
        self.logger = logging.getLogger(__name__)
        self.packet_def = packet_def
        self.field_builder = FieldBuilder(packet_def)
    
    def build(self, cmd_code: str, fields: Dict[str, Any], seq: int = 1, addr: int = 0) -> Optional[bytes]:
        """構建封包"""
        try:
            definition = self.packet_def.get_definition(cmd_code)
            if not definition:
                self.logger.error(f"未找到封包定義: {cmd_code}")
                return None
            
            payload = self._build_payload(definition, fields)
            if payload is None:
                return None
            
            return MessageFrame.encode(seq, addr, payload)
            
        except Exception as e:
            self.logger.error(f"構建封包失敗: {e}", exc_info=True)
            return None
    
    def _build_payload(self, definition: Dict[str, Any], fields: Dict[str, Any]) -> Optional[bytes]:
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
            self.logger.error(f"未知群組: {group}")
            return None
        
        payload.append(command)
        
        # 構建字段
        if "fields" in definition:
            for field in definition["fields"]:
                field_name = field["name"]
                if field_name in fields:
                    field_bytes = self.field_builder.build_field(field, fields[field_name])
                    payload.extend(field_bytes)
        
        return bytes(payload)
        