"""
封包處理器
"""

import logging
from os import strerror
from typing import Dict
from ..definitions.registry import DefinitionRegistry
from .packet_handler import PacketHandler
class PacketProcessor():
    """封包處理器"""
    
    def __init__(self, registry: DefinitionRegistry):
        self.logger = logging.getLogger(__name__)
        self.registry = registry
        self.handler = PacketHandler()
    
    def process(self, packet: Dict):
        """處理封包"""
        if not packet:
            return
        
        # 直接委託給統一的 Handler
        self.handler.process(packet)

