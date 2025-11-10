"""
基礎構建器抽象類
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseBuilder(ABC):
    """構建器基類"""
    
    @abstractmethod
    def build(self, cmd_code: str, fields: Dict, seq: int = 1, addr: int = 0) -> Optional[bytes]:
        """構建封包"""
        pass

