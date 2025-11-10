from .base import FIELD_TYPES, VALIDATORS
from .group_5f import F5_GROUP_DEFINITIONS
from .group_0f import F0_GROUP_DEFINITIONS
from .registry import DefinitionRegistry

# 合并所有定义
PACKET_DEFINITIONS = {
    **F5_GROUP_DEFINITIONS,
    **F0_GROUP_DEFINITIONS
}

__all__ = [
    'PACKET_DEFINITIONS',
    'FIELD_TYPES',
    'VALIDATORS',
    'F5_GROUP_DEFINITIONS',
    'F0_GROUP_DEFINITIONS',
    'DefinitionRegistry'
]

