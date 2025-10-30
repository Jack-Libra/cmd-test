import json
import logging
from pathlib import Path
from datetime import datetime

class PacketProcessor:
    """封包處理器（儲存、記錄、顯示）"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def process(self, parsed: dict):
        """處理解析後的封包"""
        cmd = parsed.get('cmd')
        
        # 5F 群組
        if cmd == '5F03':
            self._process_5f03(parsed)
        elif cmd == '5F0C':
            self._process_5f0c(parsed)
        elif cmd == '5FC0':
            self._process_5fc0(parsed)
        elif cmd == '5F00':
            self._process_5f00(parsed)
        elif cmd == '5FC8':
            self._process_5fc8(parsed)
        
        # 0F 群組
        elif cmd == '0F80':
            self._process_0f80(parsed)
        elif cmd == '0F81':
            self._process_0f81(parsed)
        
        
        else:
            self.logger.warning(f"未處理的命令: {cmd}")
    
    def _process_5f03(self, data: dict):
        """處理 5F03 時相資料維管理（主動回報步階轉換）"""
        # 解析 StepID 特殊狀態
        step_map = {
            0x9F: "啟動全紅3秒",
            0xAF: "結束全紅",
            0xCF: "回家時間閃光",
            0xDF: "現場操作閃光",
            0xEF: "電源異常閃光",
            0xFF: "時制異常閃光"
        }
        step_desc = step_map.get(data['step_id'], f"步階{data['step_id']}")
        
        self.logger.info(
            f"[5F03] 📊 時相資料回報 - "
            f"SEQ:{data['seq']}, "
            f"ADDR:0x{data['addr']:04X}, "
            f"PhaseOrder:0x{data['phase_order']:02X}, "
            f"SubPhase:{data['sub_phase_id']}, "
            f"Step:{step_desc}, "
            f"StepSec:{data['step_sec']}秒, "
            f"Status:0x{data['signal_status']:02X}"
        )
        self._save_json('5F03', data)
    
    def _process_5f0c(self, data: dict):
        """處理 5F0C 時相步階變換控制管理（主動回報現行時相及步階）"""
        # 解析 ControlStrategy 參考 5FH+10H
        control_desc = self._decode_control_strategy(data['control_strategy'])
        
        self.logger.info(
            f"[5F0C] 🔄 時相步階變換回報 - "
            f"SEQ:{data['seq']}, "
            f"ADDR:0x{data['addr']:04X}, "
            f"Control:{control_desc}, "
            f"SubPhase:{data['sub_phase_id']}, "
            f"Step:{data['step_id']}"
        )
        self._save_json('5F0C', data)
    
    def _process_0f80(self, data: dict):
        """處理 0F80 訊息回應（有效）"""
        
        self.logger.info(
            f"[0F80] ✅ 訊息回應有效 - "
            f"SEQ:{data['seq']}, "
            f"ADDR:0x{data['addr']:04X}, "
            f"CommandID:0x{data['command_id']:04X}"
        )
        self._save_json('0F80', data)
    
    def _process_0f81(self, data: dict):
        """處理 0F81 訊息回應（無效）"""
        
        # 找出所有錯誤類型
        error_list = []
        error_desc_map = {
            "invalid_msg": "無此訊息",
            "no_response": "無法應答資料",
            "param_invalid": "參數值無效",
            "no_param": "位元組無參數",
            "prep_error": "設備別錯誤",
            "timeout": "逾時",
            "exceed_limit": "參數值超過限",
            "reported": "已被訊息等級"
        }
        
        for key, val in data['errors'].items():
            if val:
                error_list.append(error_desc_map.get(key, key))
        
        error_desc = ", ".join(error_list) if error_list else "未知錯誤"
        
        param_info = ""
        if data['errors'].get('param_invalid') and data['param_num'] > 0:
            param_info = f", 錯誤參數編號:{data['param_num']}"
        
        self.logger.warning(
            f"[0F81] ❌ 訊息回應無效 - "
            f"SEQ:{data['seq']}, "
            f"ADDR:0x{data['addr']:04X}, "
            f"CommandID:0x{data['command_id']:04X}, "
            f"ErrorCode:0x{data['error_code']:02X} ({error_desc}){param_info}"
        )
        self._save_json('0F81', data)
    
    def _process_5fc0(self, data: dict):
        """處理控制策略回報"""
        control_desc = self._decode_control_strategy(data['control'])
        self.logger.info(
            f"[5FC0] 控制策略回報 - "
            f"SEQ:{data['seq']}, "
            f"ADDR:0x{data['addr']:04X}, "
            f"Control:{control_desc}, "
            f"EffectTime:{data['effect_time']}分"
        )
        self._save_json('5FC0', data)
    
    def _process_5f00(self, data: dict):
        """處理主動回報"""
        status_map = {0:"結束", 1:"啟動", 2:"緊急車輛", 3:"車流壅塞"}
        status = status_map.get(data['begin_end'], f"未知({data['begin_end']})")
        control_desc = self._decode_control_strategy(data['control'])
        
        self.logger.info(
            f"[5F00] 主動回報 - "
            f"SEQ:{data['seq']}, "
            f"ADDR:0x{data['addr']:04X}, "
            f"Control:{control_desc}, "
            f"Status:{status}"
        )
        self._save_json('5F00', data)
    
    def _process_5fc8(self, data: dict):
        """處理時制計畫回報"""
        self.logger.info(
            f"[5FC8] 時制計畫回報 - "
            f"SEQ:{data['seq']}, "
            f"ADDR:0x{data['addr']:04X}, "
            f"PlanID:{data['plan_id']}, "
            f"Cycle:{data['cycle_time']}秒, "
            f"Offset:{data['offset']}秒"
        )
        self._save_json('5FC8', data)
    
    def _decode_control_strategy(self, control: int) -> str:
        """解碼控制策略（參考 5FH+10H 規格）"""
        strategies = []
        if control & 0x01: strategies.append("定時控制")
        if control & 0x02: strategies.append("人工控制")
        if control & 0x04: strategies.append("公車優先")
        if control & 0x08: strategies.append("警察手控")
        if control & 0x10: strategies.append("緊急優先")
        if control & 0x20: strategies.append("即時控制")
        if control & 0x40: strategies.append("全動態控制")
        
        return f"0x{control:02X}({', '.join(strategies) if strategies else '無'})"
    

     
    def _save_json(self, cmd: str, data: dict):
        """儲存為 JSON 檔案"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.data_dir / f"{cmd}_{timestamp}.json"
        data['timestamp'] = datetime.now().isoformat()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)