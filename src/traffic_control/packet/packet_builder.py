"""
封包構建器

負責構建封包，並返回構建結果
"""

import logging
from typing import Dict, Any, Optional, Protocol
from utils import encode


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
        """構建單個字段為字節（完全使用 FIELD_TYPES）"""
        field_type = field.get("type")
        
        # list : item_type
        # 其他 : field_type
        target_type = field.get("item_type", field_type) if field_type == "list" else field_type
        
        # 從 FIELD_TYPES 獲取 builder
        # 類型固定lambda函數
        type_def = self.packet_def.get_field_type(target_type)

        builder = type_def["builder"] if type_def else b""
        
        # list 類型：遍歷構建；單一類型：直接構建
        if field_type == "list":
            return b"".join(builder(item) for item in value) if isinstance(value, list) else b""
        return builder(value)
       


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
            
            # 編碼封包
            # DLE溢出 checksum
            return encode(seq, addr, payload)
            
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
        for field in definition["fields"]:
            
            field_name = field["name"]
            if field_name in fields:
                field_bytes = self.field_builder.build_field(field, fields[field_name])
                payload.extend(field_bytes)
        
        return bytes(payload)
        