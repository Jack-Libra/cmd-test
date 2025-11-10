"""
基礎處理器抽象類
"""

from abc import ABC, abstractmethod
from typing import Dict

class BaseProcessor(ABC):
    """處理器基類"""
    
    @abstractmethod
    def process(self, packet: Dict):
        """處理封包"""
        pass

