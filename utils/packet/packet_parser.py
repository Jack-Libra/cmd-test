import logging
from typing import Optional
from utils.core import MessageFrame, Ack, Nak

class PacketParser:
    """封包解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, frame: bytes) -> Optional[dict]:
        """解析封包，返回結構化資料"""
        try:
            decoded = MessageFrame.decode(frame)
            
            # ACK 框
            if decoded.get('type') == 'ACK':
                return {
                    "type": "ACK",
                    "reply_type": "none",  # 不需要回覆
                    "seq": decoded['seq'],
                    "addr": decoded['addr'],
                    "cmd": "ACK"
                }
            
            # 訊息框
            if 'info' in decoded:
                info = decoded['info']
                
                if not info or len(info) < 2:
                    self.logger.error(f"資料錯誤: {len(info)} < 2")
                    return None
                
                # 根據第一個 byte 判斷群組
                if info[0] == 0x5F:
                    return self._parse_5f(decoded, info)
                elif info[0] == 0x0F:
                    return self._parse_0f(decoded, info)
            
            return None
            
        except Exception as e:
            self.logger.error(f"解析失敗: {e}")
            return None
    
    def _parse_5f(self, msg: dict, info: bytes) -> Optional[dict]:
        """解析 5F 群組"""
        cmd = info[1]
        base = {"seq": msg['seq'], "addr": msg['addr'], "group": "5F", "type": "MESSAGE"}
        
        # 5F 03: 時相資料維管理（主動回報 - 不需回覆 ACK）
        if cmd == 0x03:
            if len(info) < 10:
                self.logger.error(f"5F03資料錯誤: {len(info)} < 10")
                return None
            
            phase_order = info[2]
            signal_map = info[3]
            signal_count = info[4]
            signal_status = info[5]
            sub_phase_id = info[6]
            step_id = info[7]
            step_sec = int.from_bytes(info[8:10], 'big')
            
            base.update({
                "cmd": "5F03",
                "reply_type": "none",  # 主動回報，不需回覆
                "phase_order": phase_order,
                "signal_map": signal_map,
                "signal_count": signal_count,
                "signal_status": signal_status,
                "sub_phase_id": sub_phase_id,
                "step_id": step_id,
                "step_sec": step_sec
            })
            return base
        
        # 5F 0C: 時相步階變換控制管理（主動回報 - 不需回覆 ACK）
        elif cmd == 0x0C:
            if len(info) != 5:
                self.logger.error(f"5F0C資料錯誤: {len(info)} != 5")
                return None
            
            base.update({
                "cmd": "5F0C",
                "reply_type": "none",  # 主動回報，不需回覆
                "control_strategy": info[2],
                "sub_phase_id": info[3],
                "step_id": info[4]
            })
            return base
        
        # 5F C0: 控制策略回報（查詢回報 - 需要回覆 ACK）
        elif cmd == 0xC0:
            if len(info) != 4:
                self.logger.error(f"5FC0資料錯誤: {len(info)} != 4")
                return None
            base.update({
                "cmd": "5FC0",
                "reply_type": "ack",  # 查詢回報，需要回覆 ACK
                "control": info[2],
                "effect_time": info[3]
            })
            return base
        
        # 5F 00: 主動回報（不需回覆 ACK）
        elif cmd == 0x00:
            if len(info) != 4:
                self.logger.error(f"5F00資料錯誤: {len(info)} != 4")
                return None
            base.update({
                "cmd": "5F00",
                "reply_type": "none",  # 主動回報，不需回覆
                "control": info[2],
                "begin_end": info[3]
            })
            return base
        
        # 5F C8: 時制計畫回報（查詢回報 - 需要回覆 ACK）
        elif cmd == 0xC8:
            if len(info) < 6:
                self.logger.error(f"5FC8資料錯誤: {len(info)} < 6")
                return None
            plan_id, direct, phase_order, sub_cnt = info[2:6]
            need = 6 + sub_cnt + 2
            if len(info) < need:
                return None
            greens = list(info[6:6+sub_cnt])
            cycle, offset = info[6+sub_cnt], info[6+sub_cnt+1]
            base.update({
                "cmd": "5FC8",
                "reply_type": "ack",  # 查詢回報，需要回覆 ACK
                "plan_id": plan_id,
                "direct": direct,
                "phase_order": phase_order,
                "sub_phase_count": sub_cnt,
                "greens": greens,
                "cycle_time": cycle,
                "offset": offset
            })
            return base
        
        # 5F 08: 現場操作回報（主動回報 - 不需回覆 ACK）
        elif cmd == 0x08:
            if len(info) != 3:  # 5F 08 + FieldOperate(1)
                self.logger.error(f"5F08資料錯誤: {len(info)} != 3")
                return None
            
            field_operate = info[2]
            field_operate_map = {
                0x01: "現場手動",
                0x02: "現場全紅",
                0x40: "現場閃光",
                0x80: "上次現場操作回復"
            }
            field_operate_desc = field_operate_map.get(field_operate, f"未知操作碼(0x{field_operate:02X})")
            
            base.update({
                "cmd": "5F08",
                "reply_type": "none",  # 主動回報，不需回覆
                "field_operate": field_operate,
                "field_operate_desc": field_operate_desc
            })
            return base
        return None
    
    def _parse_0f(self, msg: dict, info: bytes) -> Optional[dict]:
        """解析 0F 群組（訊息回應）"""
        cmd = info[1]
        base = {"seq": msg['seq'], "addr": msg['addr'], "group": "0F", "type": "MESSAGE"}
        
        # 0F 80: 設定回報（有效）（查詢回報 - 需要回覆 ACK）
        if cmd == 0x80:
            if len(info) < 4:
                return None
            command_id = int.from_bytes(info[2:4], 'big')
            base.update({
                "cmd": "0F80",
                "reply_type": "ack",  # 查詢回報，需要回覆 ACK
                "command_id": command_id,
                "valid": True
            })
            return base
        
        # 0F 81: 設定/查詢回報（無效）（查詢回報 - 需要回覆 ACK）
        elif cmd == 0x81:
            if len(info) < 5:
                return None
            
            command_id = int.from_bytes(info[2:4], 'big')
            error_code = info[4]
            param_num = info[5] if len(info) > 5 else None
            
            errors = {
                "invalid_msg": bool(error_code & 0x01),
                "no_response": bool(error_code & 0x02),
                "param_invalid": bool(error_code & 0x04),
                "no_param": bool(error_code & 0x08),
                "prep_error": bool(error_code & 0x10),
                "timeout": bool(error_code & 0x20),
                "exceed_limit": bool(error_code & 0x40),
                "reported": bool(error_code & 0x80)
            }
            
            base.update({
                "cmd": "0F81",
                "reply_type": "ack",  # 查詢回報，需要回覆 ACK
                "command_id": command_id,
                "valid": False,
                "error_code": error_code,
                "param_num": param_num,
                "errors": errors
            })
            return base
        
        return None