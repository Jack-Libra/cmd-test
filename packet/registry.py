"""
封包處理註冊中心
統一管理解析器、構建器、處理器
"""

import logging
from typing import Dict, Optional
from .definitions.registry import DefinitionRegistry
from .parser.data_driven_parser import DataDrivenParser
from .builder.data_driven_builder import DataDrivenBuilder
from .processor.packet_processor import PacketProcessor
from core.frame import AckFrame

class PacketRegistry:
    """封包處理註冊中心"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.definitions = DefinitionRegistry()
        self.parser = DataDrivenParser(self.definitions)
        self.builder = DataDrivenBuilder(self.definitions)
        self.processor = PacketProcessor(self.definitions)
    
    def parse(self, frame: bytes) -> Optional[Dict]:
        """解析封包（資料驅動）"""
        return self.parser.parse(frame)
    
    def build(self, cmd_code: str, fields: Dict, seq: int = 1, addr: int = 0) -> Optional[bytes]:
        """構建封包"""
        return self.builder.build(cmd_code, fields, seq, addr)
    
    def process(self, packet: Dict):
        """處理封包"""
        self.processor.process(packet)
    
    def create_ack(self, seq: int, addr: int) -> bytes:
        """創建ACK幀"""
        return AckFrame.encode(seq, addr)
    
    def get_definition(self, cmd_code: str) -> Optional[Dict]:
        """獲取封包定義"""
        return self.definitions.get_definition(cmd_code)
    
    def register_definition(self, cmd_code: str, definition: Dict):
        """註冊新封包定義"""
        self.definitions.register_definition(cmd_code, definition)
        self.logger.info(f"註冊新封包定義: {cmd_code}")



