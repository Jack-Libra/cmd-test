"""
資料驅動封包構建器
"""

import logging
from typing import Dict, Optional
from core.frame import MessageFrame
from ..definitions.registry import DefinitionRegistry
from .field_builder import FieldBuilder

class DataDrivenBuilder:
    """資料驅動封包構建器（資料驅動）"""
    
    def __init__(self, registry: DefinitionRegistry):
        self.logger = logging.getLogger(__name__)
        self.registry = registry
        self.field_builder = FieldBuilder(self.registry)
    
    def build(self, cmd_code: str, fields: Dict, seq: int = 1, addr: int = 0):
        """構建封包（資料驅動）"""
        try:
            definition = self.registry.get_definition(cmd_code)
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
    
    def _build_payload(self, definition: Dict, fields: Dict):
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
            field_data = self.field_builder.build_fields(definition["fields"], fields)
            payload.extend(field_data)
        
        # 構建動態字段
        if "dynamic_fields" in definition:
            dynamic_data = self.field_builder.build_dynamic_fields(
                definition["dynamic_fields"], fields
            )
            payload.extend(dynamic_data)
        
        return bytes(payload)

