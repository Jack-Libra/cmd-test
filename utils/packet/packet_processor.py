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
        frame_type = parsed.get('type')
        cmd = parsed.get('指令')
        info = {}


        if frame_type == 'ACK':
            info = self._process_ack(parsed)
            return info


        # 5F 群組
        if cmd == '5F03':
            info = self._process_5f03(parsed)
        elif cmd == '5F0C':
            info = self._process_5f0c(parsed)
        elif cmd == '5FC0':
            info = self._process_5fc0(parsed)
        elif cmd == '5F00':
            info = self._process_5f00(parsed)
        elif cmd == '5FC8':
            info = self._process_5fc8(parsed)
        elif cmd == '5F08':
            info = self._process_5f08(parsed)
        
        # 0F 群組
        elif cmd == '0F80':
            info = self._process_0f80(parsed)
        elif cmd == '0F81':
            info = self._process_0f81(parsed)
        
        else:
            self.logger.warning(f"未處理的命令: {cmd}")
            return None

        return info
    
    def _process_ack(self, data: dict):
        """處理 ACK 確認"""
        return {
            "類型": "ACK",
            "序號": data['seq'],
            "位址": f"0x{data['addr']:04X}"
        }

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
        
        return {
            "指令": "5F03",
            "序號": data['seq'],
            "控制器編號": f"TC{data['addr']:03X}",
            "時相順序": f"0x{data['phase_order']:02X}",
            "子時相": data['sub_phase_id'],
            "步階": step_desc,
            "步階時間": f"{data['step_sec']}秒",
            "狀態": f"0x{data['signal_status']:02X}"
        }
    
    def _process_5f0c(self, data: dict):
        """處理 5F0C 時相步階變換控制管理（主動回報現行時相及步階）"""
        # 解析 ControlStrategy 參考 5FH+10H
        control_desc = self._decode_control_strategy(data['control_strategy'])
        
        return {
            "指令": "5F0C",
            "序號": data['seq'],
            "位址": f"0x{data['addr']:04X}",
            "控制策略": control_desc,
            "子時相": data['sub_phase_id'],
            "步階": data['step_id']
        }
    
    def _process_0f80(self, data: dict):
        """處理 0F80 訊息回應（有效）"""
        
        return {
            "指令": "0F80",
            "序號": data['seq'],
            "位址": f"0x{data['addr']:04X}",
            "命令ID": f"0x{data['command_id']:04X}",
            "狀態": "有效"
        }
    
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
        
        info = {
            "指令": "0F81",
            "序號": data['seq'],
            "控制器編號": f"TC{data['addr']:03X}",
            "命令ID": f"0x{data['command_id']:04X}",
            "狀態": "無效",
            "錯誤碼": f"0x{data['error_code']:02X}",
            "錯誤描述": error_desc
        }
        
        if data['errors'].get('param_invalid') and data.get('param_num') and data['param_num'] > 0:
            info["錯誤參數編號"] = data['param_num']
        
        return info
    
    def _process_5fc0(self, data: dict):
        """處理控制策略回報"""
        control_desc = self._decode_control_strategy(data['control'])
        return {
            "指令": "5FC0",
            "序號": data['seq'],
            "控制器編號": f"TC{data['addr']:03X}",
            "控制策略": control_desc,
            "生效時間": f"{data['effect_time']}分"
        }
    
    def _process_5f00(self, data: dict):
        """處理主動回報"""
        status_map = {0:"結束", 1:"啟動", 2:"緊急車輛", 3:"車流壅塞"}
        status = status_map.get(data['begin_end'], f"未知({data['begin_end']})")
        control_desc = self._decode_control_strategy(data['control'])
        
        return {
            "指令": "5F00",
            "序號": data['seq'],
            "控制器編號": f"TC{data['addr']:03X}",
            "控制策略": control_desc,
            "狀態": status
        }
    
    def _process_5fc8(self, data: dict):
        """處理時制計畫回報"""
        return {
            "指令": "5FC8",
            "序號": data['seq'],
            "控制器編號": f"TC{data['addr']:03X}",
            "計畫ID": data['plan_id'],
            "週期時間": f"{data['cycle_time']}秒",
            "偏移時間": f"{data['offset']}秒"
        }
    
    def _process_5f08(self, data: dict):
        """處理現場操作回報"""
        return {
            "指令": "5F08",
            "序號": data['seq'],
            "控制器編號": f"TC{data['addr']:03X}",
            "現場操作": data['現場操作碼']
        }

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