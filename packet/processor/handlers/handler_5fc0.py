"""
5FC0 控制策略回報處理器
"""

import logging
from typing import Dict
from .handler_base import BaseHandler

class Handler5FC0(BaseHandler):
    """5FC0 控制策略回報處理器"""
    
    def process(self, packet: Dict):
        """處理5FC0封包（控制策略回報）"""
        tc_id = packet.get("tc_id", 0)
        control_strategy = packet.get("control_strategy", 0)
        effect_time = packet.get("effect_time", 0)
        strategy_details = packet.get("control_strategy_details", {})
        
        strategy_desc = self._get_strategy_desc(strategy_details)
        
        self.logger.info(
            f"TC{tc_id:03d} 5FC0: 控制策略回報 - {strategy_desc}, "
            f"有效時間={effect_time}分鐘, 策略碼=0x{control_strategy:02X}"
        )
    
    def _get_strategy_desc(self, strategy_details: Dict) -> str:
        """獲取策略描述（控制策略回報）"""
        strategy_map = {
            "fixed_time": "定時控制",
            "dynamic": "動態控制",
            "intersection_manual": "路口手動",
            "central_manual": "中央手動",
            "phase_control": "時相控制",
            "immediate_control": "即時控制",
            "actuated": "觸動控制",
            "special_route": "特別路線控制"
        }
        
        result = []
        for key, desc in strategy_map.items():
            if strategy_details.get(key, False):
                result.append(desc)
        
        return "、".join(result) if result else "無設定策略"

