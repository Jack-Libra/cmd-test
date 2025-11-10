"""
定義註冊表
"""

from typing import Dict, Optional
from .base import FIELD_TYPES, VALIDATORS
from .group_5f import F5_GROUP_DEFINITIONS
from .group_0f import F0_GROUP_DEFINITIONS

class DefinitionRegistry:
    """定義註冊表"""
    
    def __init__(self):
        self.definitions = {
            **F5_GROUP_DEFINITIONS,
            **F0_GROUP_DEFINITIONS
        }
        self.field_types = FIELD_TYPES
        self.validators = VALIDATORS
    
    def get_definition(self, cmd_code: str) -> Optional[Dict]:
        """獲取封包定義"""
        return self.definitions.get(cmd_code)
    
    def register_definition(self, cmd_code: str, definition: Dict):
        """註冊新封包定義"""
        self.definitions[cmd_code] = definition
    
    def get_field_type(self, field_type: str) -> Optional[Dict]:
        """獲取字段類型定義"""
        return self.field_types.get(field_type)
    
    def get_validator(self, validator_type: str):
        """獲取驗證器"""
        return self.validators.get(validator_type)

