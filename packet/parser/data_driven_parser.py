"""
資料驅動封包解析器
"""

import logging
import binascii
from typing import Dict
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
    
    def parse(self, frame: bytes):
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
    
    def can_parse(self, frame: bytes):
        """判斷是否能解析"""
        try:
            decoded = self.frame_decoder.decode(frame)
            return decoded["type"] in ["ACK", "STX"]
        except:
            return False
    
    def _parse_stx(self, decoded: Dict, frame: bytes):
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
            #self.logger.error(f"未定義的指令碼: {cmd_code}")
            return
        
        header = {
        "seq": decoded["seq"],
        "addr": decoded["addr"],
        "len": decoded["len"]
        }
        
        # 解析封包
        return self._parse_by_definition(definition, header, payload, cmd_code, frame)
    
    
    def _parse_by_definition(self, definition, header, 
                            payload, cmd_code, frame):
        """根據定義解析封包 - 統一處理所有字段"""
        # 基礎字段
        result = {
            "序列號": header["seq"],
            "號誌控制器ID": header["addr"],
            "欄位長度": header["len"],
            "指令編號": cmd_code,
            "指令": definition.get("name", ""),
            "回覆類型": definition.get("reply_type", ""),
            "needs_ack": definition.get("needs_ack", False),
            "原始封包": binascii.hexlify(frame).decode('ascii')
        }
        
        # 解析payload字段
        if "fields" in definition:
            result = self.field_parser.parse_fields(
                payload, definition["fields"], result
            )     
        return result
    



