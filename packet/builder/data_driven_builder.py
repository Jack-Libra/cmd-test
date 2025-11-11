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
            
            # 構建INFO字段
            info = self._build_info(definition, fields)
            if info is None:
                return None
            
            # 構建完整幀
            frame = MessageFrame.encode(seq, addr, info)
            return frame
            
        except Exception as e:
            self.logger.error(f"構建封包失敗: {e}", exc_info=True)
            return None
    
    def _build_info(self, definition: Dict, fields: Dict):
        """構建INFO字段"""
        info = bytearray()
        
        # 添加指令碼
        group = definition.get("group", "")
        command = definition.get("command", 0)
        
        if group == "5F":
            info.append(0x5F)
        elif group == "0F":
            info.append(0x0F)
        else:
            self.logger.error(f"未知群组: {group}")
            return None
        
        info.append(command)
        
        # 構建靜態字段
        if "fields" in definition:
            field_data = self.field_builder.build_fields(definition["fields"], fields)
            info.extend(field_data)
        
        # 構建動態字段
        if "dynamic_fields" in definition:
            dynamic_data = self.field_builder.build_dynamic_fields(
                definition["dynamic_fields"], fields
            )
            info.extend(dynamic_data)
        
        return bytes(info)

