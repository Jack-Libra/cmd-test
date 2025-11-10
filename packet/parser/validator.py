"""
封包驗證器
"""

from typing import Dict
from ..definitions.registry import DefinitionRegistry

class PacketValidator:
    """封包驗證器"""
    
    def __init__(self, registry: DefinitionRegistry):
        self.registry = registry
    
    def validate(self, frame: bytes, definition: Dict) -> bool:
        """驗證封包"""
        validation = definition.get("validation")
        if not validation:
            return True
        
        validator_type = validation.get("type")
        value = validation.get("value")
        
        if validator_type == "custom":
            func = validation.get("func")
            return func(frame) if func else True
        
        validator = self.registry.get_validator(validator_type)
        if validator:
            return validator(frame, value)
        
        return True

