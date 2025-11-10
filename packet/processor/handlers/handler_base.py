"""
基礎處理器抽象類
"""

import logging
from typing import Dict

class BaseHandler:
    """基礎處理器抽象類"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process(self, packet: Dict):
        """處理封包（默認實現）"""
        command = packet.get("指令", "Unknown")
        tc_id = packet.get("tc_id", 0)
        self.logger.info(f"TC{tc_id:03d} 收到封包: {command}")

