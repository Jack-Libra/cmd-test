"""
資料驅動封包解析器
"""

import logging
import binascii
import datetime
from typing import Optional, Dict, Any
from core.frame import FrameDecoder
from ..definitions.registry import DefinitionRegistry

from .unified_field_parser import UnifiedFieldParser

class DataDrivenParser():
    """資料驅動封包解析器"""
    
    def __init__(self, registry: DefinitionRegistry):
        self.logger = logging.getLogger(__name__)
        self.registry = registry
        self.field_parser = UnifiedFieldParser(self.registry)
        self.frame_decoder = FrameDecoder()
    
    def parse(self, frame: bytes) -> Optional[Dict[str, Any]]:
        """解析封包"""
        try:
            decoded = self.frame_decoder.decode(frame)
            
            # ACK 框處理
            if decoded["type"] == "ACK":
                return {
                    "type": "ACK",
                    "seq": decoded["seq"],
                    "addr": decoded["addr"],
                    "len": decoded["len"]
                }
            
            # STX 框處理
            if decoded["type"] == "STX":
                return self._parse_stx(decoded, frame)
            
            return None
            
        except Exception as e:
            self.logger.error(f"解析失敗: {e}", exc_info=True)
            return None
    
    def can_parse(self, frame: bytes) -> bool:
        """判斷是否能解析"""
        try:
            decoded = self.frame_decoder.decode(frame)
            return decoded["type"] in ["ACK", "STX"]
        except:
            return False
    
    def _parse_stx(self, decoded: Dict, frame: bytes) -> Optional[Dict]:
        """解析 STX 框"""
        payload = decoded["payload"]  # 純淨的 INFO 數據
        
        if len(payload) < 2:
            return None
        
        # 構建指令碼
        command_prefix = payload[0]
        command_suffix = payload[1]
        cmd_code = f"{command_prefix:02X}{command_suffix:02X}"
        
        # 查找定義
        definition = self.registry.get_definition(cmd_code)
        if not definition:
            self.logger.warning(f"未定義的指令碼: {cmd_code}")
            return self._parse_unknown(cmd_code, decoded, frame)
        
        
        # 解析封包（跳過指令碼部分）
        info_payload = payload[2:]  # 跳過 5F 03
        return self._parse_by_definition(definition, decoded["header"], info_payload, frame)
    
    
    def _parse_by_definition(self, definition: Dict, header: Dict, 
                            info_payload: bytes, frame: bytes) -> Dict:
        """根據定義解析封包 - 統一處理所有字段"""
        # 基礎字段
        result = {
            "seq": header["seq"],
            "addr": header["addr"],
            "tc_id": header["addr"],
            "len": header["len"],
            "command": definition.get("name", "").split()[0] if definition.get("name") else "",
            "指令": definition.get("name", ""),
            "回覆類型": definition.get("reply_type", ""),
            "needs_ack": definition.get("needs_ack", False),
            "raw_data": binascii.hexlify(frame).decode('ascii'),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 統一解析所有字段
        if "fields" in definition:
            result = self.field_parser.parse_all_fields(
                info_payload, definition["fields"], result
            )
        
        return result
    
    def _parse_unknown(self, cmd_code: str, decoded: Dict, frame: bytes) -> Dict:
        """處理未知封包"""
        return {
            "seq": decoded["seq"],
            "addr": decoded["addr"],
            "tc_id": decoded["addr"],
            "指令": cmd_code,
            "raw_data": binascii.hexlify(frame).decode('ascii'),
            "status": "unknown",
            "length": len(frame),
            "timestamp": datetime.datetime.now().isoformat()
        }

