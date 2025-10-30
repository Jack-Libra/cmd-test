import logging
from typing import Optional
from utils.core import MessageFrame

class PacketParser:
    """封包解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, frame: bytes) -> Optional[dict]:
        """解析封包，返回結構化資料"""
        try:
            msg = MessageFrame.decode(frame)
            info = msg['info']
            
            if not info or len(info) < 2:
                return {"error": "封包解析失敗"}
            
            # 根據第一個 byte 判斷群組
            if info[0] == 0x5F:
                return self._parse_5f(msg, info)
            elif info[0] == 0x0F:
                return self._parse_0f(msg, info)
            
            return {"error": "未知的封包群組"}
            
        except Exception as e:
            self.logger.error(f"解析失敗: {e}")
            return {"error": f"解析失敗: {e}"}
    
    def _parse_5f(self, msg: dict, info: bytes) -> Optional[dict]:
        """解析 5F 群組"""
        cmd = info[1]
        base = {"seq": msg['seq'], "addr": msg['addr'], "group": "5F"}
        
        # 5F 03: 時相資料維管理（主動回報步階轉換）
        if cmd == 0x03:
            if len(info) < 10:
                return {"error": "封包解析失敗"}
            
            phase_order = info[2]
            signal_map = info[3]
            signal_count = info[4]
            signal_status = info[5]
            sub_phase_id = info[6]
            step_id = info[7]
            step_sec = int.from_bytes(info[8:10], 'big')  # Up/Down Count
            
            base.update({
                "cmd": "5F03",
                "phase_order": phase_order,
                "signal_map": signal_map,
                "signal_count": signal_count,
                "signal_status": signal_status,
                "sub_phase_id": sub_phase_id,
                "step_id": step_id,
                "step_sec": step_sec
            })
            return base
        
        # 5F 0C: 時相步階變換控制管理（主動回報現行時相及步階）
        elif cmd == 0x0C:
            if len(info) != 5:
                return {"error": "封包解析失敗"}
            
            base.update({
                "cmd": "5F0C",
                "control_strategy": info[2],
                "sub_phase_id": info[3],
                "step_id": info[4]
            })
            return base
        
        # 5F C0: 控制策略回報
        elif cmd == 0xC0:
            if len(info) != 4:
                return {"error": "封包解析失敗"}
            base.update({
                "cmd": "5FC0",
                "control": info[2],
                "effect_time": info[3]
            })
            return base
        
        # 5F 00: 主動回報
        elif cmd == 0x00:
            if len(info) != 4:
                return {"error": "封包解析失敗"}
            base.update({
                "cmd": "5F00",
                "control": info[2],
                "begin_end": info[3]
            })
            return base
        
        # 5F C8: 時制計畫回報
        elif cmd == 0xC8:
            if len(info) < 6:
                return {"error": "封包解析失敗"}
            plan_id, direct, phase_order, sub_cnt = info[2:6]
            need = 6 + sub_cnt + 2
            if len(info) < need:
                return {"error": "封包解析失敗"}
            greens = list(info[6:6+sub_cnt])
            cycle, offset = info[6+sub_cnt], info[6+sub_cnt+1]
            base.update({
                "cmd": "5FC8",
                "plan_id": plan_id,
                "direct": direct,
                "phase_order": phase_order,
                "sub_phase_count": sub_cnt,
                "greens": greens,
                "cycle_time": cycle,
                "offset": offset
            })
            return base
        
        return {"error": "封包解析失敗"}
    
    def _parse_0f(self, msg: dict, info: bytes) -> Optional[dict]:
        """解析 0F 群組（訊息回應）"""
        cmd = info[1]
        base = {"seq": msg['seq'], "addr": msg['addr'], "group": "0F"}
        
        # 0F 80: 設定回報（有效）
        if cmd == 0x80:
            if len(info) < 4:
                return {"error": "封包解析失敗"}
            command_id = int.from_bytes(info[2:4], 'big')
            base.update({
                "cmd": "0F80",
                "command_id": command_id,
                "valid": True
            })
            return base
        
        # 0F 81: 設定/查詢回報（無效）
        elif cmd == 0x81:
            if len(info) < 5:
                return {"error": "封包解析失敗"}
            
            command_id = int.from_bytes(info[2:4], 'big')
            error_code = info[3]
            param_num = info[4]
            
            # 解析錯誤碼 bit 定義
            errors = {
                "無此訊息": bool(error_code & 0x01),        # bit0: 無此訊息
                "無法應答資料": bool(error_code & 0x02),        # bit1: 無法應答資料
                "參數值無效": bool(error_code & 0x04),      # bit2: 參數值無效
                "位元組無參數": bool(error_code & 0x08),           # bit3: 位元組無參數
                "設備別錯誤": bool(error_code & 0x10),         # bit4: 設備別錯誤
                "逾時": bool(error_code & 0x20),            # bit5: 逾時
                "參數值超過限": bool(error_code & 0x40),       # bit6: 參數值超過限
                "已被訊息等級": bool(error_code & 0x80)            # bit7: 已被訊息等級
            }
            
            base.update({
                "cmd": "0F81",
                "command_id": command_id,
                "valid": False,
                "error_code": error_code,
                "param_num": param_num,
                "errors": errors
            })
            return base
        
        return {"error": "封包解析失敗"}