# packet/processor/packet_handler.py

"""
統一封包處理器
整合所有命令的處理邏輯
"""

import json
import logging
from typing import Dict, Optional

class PacketHandler:
    """統一封包處理器"""
    
    # 策略描述映射（共享）
    STRATEGY_MAP = {
        "fixed_time": "定時控制",
        "dynamic": "動態控制",
        "intersection_manual": "路口手動",
        "central_manual": "中央手動",
        "phase_control": "時相控制",
        "immediate_control": "即時控制",
        "actuated": "觸動控制",
        "special_route": "特別路線控制"
    }
    
    # 步階信息文件路徑
    STEP_INFO_FILE = 'logs/current_step.json'
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 命令到處理方法的映射
        self.handlers = {
            "5F03": self._handle_5f03,
            "5F0C": self._handle_5f0c,
            "5FC0": self._handle_5fc0,
        }
        self.logger.info("統一封包處理器初始化")
    
    def process(self, packet: Dict):
        """處理封包（統一入口）"""
        if not packet:
            return
        
        # 獲取命令碼
        command = packet.get("指令", "")
        if not command:
            command = packet.get("command", "")
        
        # 查找對應的處理方法
        handler_method = self.handlers.get(command)
        if handler_method:
            handler_method(packet)
        else:
            self.logger.error(f"未找到處理器: {command}")
    
    def _handle_5f03(self, packet: Dict):
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
            with open(self.STEP_INFO_FILE, 'w') as file:
                json.dump(current_dict, file)
        except Exception as e:
            self.logger.error(f"保存步階信息失敗: {e}")
        
        # 記錄日誌
        self.logger.info(
            f"TC{tc_id:03d} 5F03: 時相={phase_order:02X}, "
            f"分相={sub_phase_id}, 步階={step_id}, 秒數={step_sec}"
        )
    
    def _handle_5f0c(self, packet: Dict):
        """處理5F0C封包（時相步階變換控制管理）"""
        tc_id = packet.get("tc_id", 0)
        sub_phase_id = packet.get("sub_phase_id", 0)
        step_id = packet.get("step_id", 0)
        control_strategy = packet.get("control_strategy", 0)
        strategy_details = packet.get("control_strategy_details", {})
        
        # 從 current_step.json 讀取步階秒數
        step_sec = self._load_step_sec()
        
        # 構建策略描述
        strategy_desc = self._get_strategy_desc(strategy_details)
        
        self.logger.info(
            f"TC{tc_id:03d} 5F0C: 策略={strategy_desc} (0x{control_strategy:02X}), "
            f"時相={sub_phase_id}, 步階={step_id}, 秒數={step_sec}"
        )
    
    def _handle_5fc0(self, packet: Dict):
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
        """獲取策略描述（共享方法）"""
        result = []
        for key, desc in self.STRATEGY_MAP.items():
            if strategy_details.get(key, False):
                result.append(desc)
        
        return "、".join(result) if result else "無設定策略"
    
    def _load_step_sec(self) -> int:
        """讀取步階秒數（共享方法）"""
        try:
            with open(self.STEP_INFO_FILE, 'r') as f:
                step_data = json.load(f)
                return step_data.get('step_sec', 0)
        except Exception as e:
            self.logger.error(f"讀取步階秒數失敗: {e}")
            return 0