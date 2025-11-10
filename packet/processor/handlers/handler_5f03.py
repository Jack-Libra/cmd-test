"""
5F03 時相資料維管理處理器
"""

import json
import logging
from typing import Dict
from .handler_base import BaseHandler
from core.utils import int_to_binary_list

class Handler5F03(BaseHandler):
    """5F03 時相資料維管理處理器"""
    
    def process(self, packet: Dict):
        """處理5F03封包（時相資料維管理）"""
        tc_id = packet.get("tc_id", 0)
        phase_order = packet.get("phase_order", 0)
        sub_phase_id = packet.get("sub_phase_id", 0)
        step_id = packet.get("step_id", 0)
        step_sec = packet.get("step_sec", 0)
        
        # 保存當前步階信息
        current_dict = {
            'sub_phase_id': sub_phase_id,
            'step_id': step_id,
            'step_sec': step_sec,
            'phase_order': f'{phase_order:02X}'.upper()
        }
        
        try:
            with open('logs/current_step.json', 'w') as file:
                json.dump(current_dict, file)
        except Exception as e:
            self.logger.error(f"保存步階信息失敗: {e}")
        
        # 記錄日誌
        self.logger.info(
            f"TC{tc_id:03d} 5F03: 時相={phase_order:02X}, "
            f"分相={sub_phase_id}, 步階={step_id}, 秒數={step_sec}"
        )

