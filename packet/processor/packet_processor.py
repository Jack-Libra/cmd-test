"""
封包處理器
"""

import logging
from typing import Dict, Optional
from ..definitions.registry import DefinitionRegistry
from .base import BaseProcessor
from .handlers import (
    BaseHandler, Handler5F03, Handler5F0C, Handler5FC0
)

class PacketProcessor(BaseProcessor):
    """封包處理器"""
    
    def __init__(self, registry: DefinitionRegistry = None):
        self.logger = logging.getLogger(__name__)
        self.registry = registry or DefinitionRegistry()
        self.handlers = self._register_handlers()
    
    def _register_handlers(self) -> Dict[str, BaseHandler]:
        """註冊處理器"""
        return {
            "5F03": Handler5F03(),
            "5F0C": Handler5F0C(),
            "5FC0": Handler5FC0(),
            # 默認處理器
            "default": BaseHandler()
        }
    
    def process(self, packet: Dict):
        """處理封包"""
        if not packet:
            return
        
        command = packet.get("指令", "")
        if not command:
            command = packet.get("command", "")
        
        # 查找處理器
        handler = self.handlers.get(command, self.handlers["default"])
        handler.process(packet)

