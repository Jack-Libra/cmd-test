"""
5F0C 時相步階變換控制管理處理器
"""

import json
import logging
from typing import Dict
from .handler_base import BaseHandler

class Handler5F0C(BaseHandler):
    """5F0C 時相步階變換控制管理處理器"""
    
    def process(self, packet: Dict):
        """處理5F0C封包（時相步階變換控制管理）"""
        tc_id = packet.get("tc_id", 0)
        sub_phase_id = packet.get("sub_phase_id", 0)
        step_id = packet.get("step_id", 0)
        control_strategy = packet.get("control_strategy", 0)
        strategy_details = packet.get("control_strategy_details", {})
        
        # 從 current_step.json 讀取步階秒數
        try:
            with open('logs/current_step.json', 'r') as f:
                step_data = json.load(f)
                step_sec = step_data.get('step_sec', 0)
        except Exception as e:
            self.logger.error(f"讀取步階秒數失敗: {e}")
            step_sec = 0
        
        # 構建策略描述（時相步階變換控制管理）
        strategy_desc = self._get_strategy_desc(strategy_details)
        
        self.logger.info(
            f"TC{tc_id:03d} 5F0C: 策略={strategy_desc} (0x{control_strategy:02X}), "
            f"時相={sub_phase_id}, 步階={step_id}, 秒數={step_sec}"
        )
    
    def _get_strategy_desc(self, strategy_details: Dict) -> str:
        """獲取策略描述（時相步階變換控制管理）"""
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

