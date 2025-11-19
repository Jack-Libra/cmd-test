"""
封包解析器 - 解耦版本
"""
import binascii
import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, NamedTuple, Tuple
from utils import FrameDecoder, int_to_binary_list
from config.log_setup import get_logger

# ============= 數據結構 =============

@dataclass
class DecodedFrame:
    """解碼後的幀數據"""
    type: str  # "ACK" 或 "STX"
    seq: int
    addr: int
    len: int
    payload: Optional[bytes] = None

@dataclass
class Packet:
    """封包數據結構"""
    seq: int  # 序列號
    tc_id: int  # 號誌控制器ID
    length: int  # 欄位長度
    cmd_code: Optional[str] = None  # 指令編號
    command: Optional[str] = None  # 指令
    reply_type: Optional[str] = None  # 訊息型態(ACK, 設定, 查詢, 設定回報, 查詢回報, 主動回報)
    needs_ack: bool = False
    raw_packet: Optional[str] = None  # 原始封包
    receive_time: Optional[str] = None  # 接收時間
    extra_fields: Dict[str, Any] = field(default_factory=dict) # 中文


# ============= 協議特殊結構定義 =============
class TimeSegment(NamedTuple):
    """時間片段結構 (Hour+Min+PlanID)"""
    hour: int
    minute: int
    plan_id: int
    
    def __str__(self):
        return f"{self.hour:02d}:{self.minute:02d} (PlanID: {self.plan_id})"
    
    def to_dict(self) -> Dict[str, int]:
        """轉換為字典"""
        return {"hour": self.hour, "minute": self.minute, "plan_id": self.plan_id}

class SignalMap:
    """號誌位置圖 - 封裝二進制表示"""
    def __init__(self, value: int):
        self.value = value
        self.binary_list = int_to_binary_list(value)
    
    def __str__(self):
        """格式化顯示"""
        return f"0x{self.value:02X} = {self.binary_list}"
    
    def __int__(self):
        """轉換為整數"""
        return self.value
    
    def __repr__(self):
        return f"SignalMap(0x{self.value:02X})"

class SignalStatusList:
    """燈號狀態列表 - 封裝格式化邏輯"""
    def __init__(self, status_bytes: List[int]):
        self.status_bytes = status_bytes
        self.formatted_lines = self._format_statuses()
    
    def _format_statuses(self) -> List[str]:
        """格式化狀態列表"""
        formatted_statuses = []
        
        for i, status_byte in enumerate(self.status_bytes, 1):
            status_list = int_to_binary_list(status_byte)
            
            # 提取行人燈位
            pedgreen_bit = status_list[6] if len(status_list) > 6 else 0
            pedred_bit = status_list[7] if len(status_list) > 7 else 0
            
            # 判斷行人燈狀態
            if pedgreen_bit and pedred_bit:
                ped_status = "行人綠燈閃爍"
            elif pedgreen_bit:
                ped_status = "行人綠燈"
            elif pedred_bit:
                ped_status = "行人紅燈"
            else:
                ped_status = None
            
            # 構建狀態描述
            status_parts = []
            
            # 車道燈狀態
            if len(status_list) > 0 and status_list[0]:
                status_parts.append("全紅")
            elif len(status_list) > 1 and status_list[1]:
                status_parts.append("黃燈")
            elif len(status_list) > 2 and status_list[2]:
                status_parts.append("綠燈")
            
            # 轉向燈狀態
            turn_parts = []
            if len(status_list) > 3 and status_list[3]:
                turn_parts.append("左轉")
            if len(status_list) > 4 and status_list[4]:
                turn_parts.append("直行")
            if len(status_list) > 5 and status_list[5]:
                turn_parts.append("右轉")
            if turn_parts:
                status_parts.append("、".join(turn_parts))
            
            # 行人燈狀態
            if ped_status:
                status_parts.append(ped_status)
            
            # 組合最終描述
            status_desc = "、".join(status_parts) if status_parts else "未知"
            formatted_statuses.append(f"   方向 {i}: {status_desc}")
        
        return formatted_statuses
    
    def __str__(self):
        """字符串表示"""
        return "\n".join(self.formatted_lines)
    
    def __iter__(self):
        """支持迭代（用於 format_packet_display）"""
        return iter(self.formatted_lines)
    
    def __len__(self):
        return len(self.formatted_lines)
    
    def __getitem__(self, index):
        return self.formatted_lines[index]


# ============= 封包解析器 =============

class PacketParser:
    """封包解析器"""
    
    def __init__(self, packet_def, mode="receive"):

        self.logger = get_logger(f"tc.{mode}")
        self.packet_def = packet_def
        self.frame_decoder = FrameDecoder()
        self.field_parser = FieldParser(packet_def)
    
    def parse(self, frame: bytes) -> Optional[Packet]:
        """解析封包"""
        
        try:
            decoded_dict = self.frame_decoder.decode(frame)
            decoded = DecodedFrame(**decoded_dict)
            
            # ACK 框處理
            if decoded.type == "ACK":
                return Packet(
                    seq=decoded.seq,
                    tc_id=decoded.addr,
                    length=decoded.len,
                    reply_type="ACK",
                    needs_ack=True,
                    raw_packet=binascii.hexlify(frame).decode('ascii'),
                    receive_time=datetime.datetime.now().isoformat()
                )
                       
            # STX 框處理
            if decoded.type == "STX":
                if not decoded.payload or len(decoded.payload) < 2:
                    return None
                
                # 構建指令碼
                cmd_code = f"{decoded.payload[0]:02X}{decoded.payload[1]:02X}"
                
                # 查找定義
                definition = self.packet_def.get_definition(cmd_code)
                
                # 創建基礎封包
                packet = Packet(
                    seq=decoded.seq,
                    tc_id=decoded.addr,
                    length=decoded.len,
                    cmd_code=cmd_code,
                    raw_packet=binascii.hexlify(frame).decode('ascii'),
                    receive_time=datetime.datetime.now().isoformat()
                )
                
                # 未定義的指令碼
                if not definition:
                    return packet
                
                # 設置定義相關字段
                packet.command = definition.get("name", "")
                packet.reply_type = definition.get("reply_type", "")
                
                # 解析字段
                if "fields" in definition:
                    packet = self.field_parser.parse_fields(
                        decoded.payload, definition["fields"], packet
                    )
                
                return packet
            
            return None
            
        except Exception as e:
            #self.logger.error(f"解析失敗: {e}", exc_info=True)
            return None
    
# ============= 字段解析器 =============

class FieldParser:
    """字段解析器"""
    
    def __init__(self, packet_def):
        self.packet_def = packet_def
        # 註冊所有解析器
        self.parsers = {
            "uint8": self._parse_uint8,
            "uint16": self._parse_uint16,
            "list": self._parse_list,
            # 專門類型解析器
            "time_segment_list": self._parse_time_segment_list,
            "weekday_list": self._parse_weekday_list,
            "signal_map": self._parse_signal_map,
            "signal_status_list": self._parse_signal_status_list,
        }  

    def parse_fields(self, payload: bytes, fields: List[Dict[str, Any]], 
                    result: Packet) -> Packet:
        """解析字段列表"""
        current_index = 0
        
        for field in fields:
            field_name = field["name"]
            field_type = field.get("type", "uint8")
            field_index = field.get("index")
            
            # 計算實際索引位置
            actual_index = field_index if field_index is not None else current_index
            
            # 獲取解析器
            parser = self.parsers.get(field_type)
            if not parser:
                result.extra_fields[field_name] = None
                continue
            
            # 解析字段
            value, next_index = parser(payload, field, actual_index, result)
            
            # 應用映射和後處理
            if value is not None:
                value = self._apply_mapping(value, field)
                result.extra_fields[field_name] = value
            else:
                result.extra_fields[field_name] = None
            
            # 更新索引（除非是動態字段）
            if field_index != "dynamic":
                current_index = next_index
        
        return result
    # ============= 基礎類型解析器 =============
    def _parse_uint8(self, payload: bytes, field: Dict[str, Any], 
                    index: int, result: Packet) -> Tuple[Optional[int], int]: 
        """解析 uint8"""
        if index >= len(payload):
            return None, index + 1
        return payload[index], index + 1    
    def _parse_uint16(self, payload: bytes, field: Dict[str, Any], 
                     index: int, result: Packet) -> Tuple[Optional[int], int]:
        """解析 uint16"""
        if index + 1 >= len(payload):
            return None, index + 2
        endian = field.get("endian", "big")
        value = int.from_bytes(payload[index:index+2], endian)
        return value, index + 2
    
    def _parse_list(self, payload: bytes, field: Dict[str, Any], 
                   index: int, result: Packet) -> Tuple[List[Any], int]:
        """解析列表字段"""
        count_from = field.get("count_from", "")
        
        # 獲取計數
        if callable(count_from):
            count = count_from(self._packet_to_dict(result))
        elif isinstance(count_from, str):
            count = result.extra_fields.get(count_from, 0)
        elif isinstance(count_from, int):
            count = count_from
        else:
            count = 0
        
        item_type = field.get("item_type", "uint8")
        items = []
        current_index = index
        
        type_def = self.packet_def.get_field_type(item_type)
        if not type_def:
            return items, current_index
        
        item_size = type_def.get("size", 1)
        for _ in range(count):
            if current_index + item_size > len(payload):
                break
            
            if item_type == "uint16":
                endian = field.get("endian", "big")
                value = int.from_bytes(
                    payload[current_index:current_index+2], endian
                )
                current_index += 2
            else:
                value = payload[current_index]
                current_index += 1
            
            items.append(value)
        
        return items, current_index
    
    # ============= 專門類型解析器 =============
    def _parse_time_segment_list(self, payload: bytes, field: Dict[str, Any], 
                                index: int, result: Packet) -> Tuple[List[TimeSegment], int]:
        """
        解析時間片段列表 (Hour+Min+PlanID)(count)
        
        專門處理多個指令共用的時間片段結構
        """
        count = result.extra_fields.get(field.get("count_from", ""), 0)
        segments = []
        current_index = index
        
        for _ in range(count):
            if current_index + 2 >= len(payload):
                break
            
            hour = payload[current_index]
            minute = payload[current_index + 1]
            plan_id = payload[current_index + 2]
            
            segments.append(TimeSegment(hour, minute, plan_id))
            current_index += 3
        
        return segments, current_index
      
    def _parse_weekday_list(self, payload: bytes, field: Dict[str, Any], 
                           index: int, result: Packet) -> Tuple[List[int], int]:
        """
        解析星期列表 Weekday(num_weekday)
        
        專門處理星期列表，帶驗證（1-7: 週一到週日, 11-17: 隔週休）
        """
        count = result.extra_fields.get(field.get("count_from", ""), 0)
        weekdays = []
        current_index = index
        
        for _ in range(count):
            if current_index >= len(payload):
                break
            
            weekday = payload[current_index]
            # 驗證範圍：1-7, 11-17
            if not (1 <= weekday <= 7 or 11 <= weekday <= 17):
                # 可以記錄警告，但繼續解析
                pass
            weekdays.append(weekday)
            current_index += 1
        
        return weekdays, current_index

     # ============= 輔助方法 =============

    def _parse_signal_map(self, payload: bytes, field: Dict[str, Any], 
                         index: int, result: Packet) -> Tuple[SignalMap, int]:
        """解析號誌位置圖"""
        if index >= len(payload):
            return SignalMap(0), index + 1
        value = payload[index]
        return SignalMap(value), index + 1
    
    def _parse_signal_status_list(self, payload: bytes, field: Dict[str, Any], 
                                  index: int, result: Packet) -> Tuple[SignalStatusList, int]:
        """解析燈號狀態列表"""
        count_from = field.get("count_from", "")
        
        # 獲取計數
        if callable(count_from):
            count = count_from(self._packet_to_dict(result))
        elif isinstance(count_from, str):
            count = result.extra_fields.get(count_from, 0)
        elif isinstance(count_from, int):
            count = count_from
        else:
            count = 0
        
        status_bytes = []
        current_index = index
        
        for _ in range(count):
            if current_index >= len(payload):
                break
            status_bytes.append(payload[current_index])
            current_index += 1
        
        return SignalStatusList(status_bytes), current_index

    # ============= 輔助方法 =============
    def _apply_mapping(self, value: Any, field: Dict[str, Any]) -> Any:
        """應用字段映射"""
        if "mapping" not in field:
            return value
        
        mapping = field["mapping"]
        try:
            # 字典映射
            return mapping.get(value, f"未知(0x{value:02X})")
        except AttributeError:
            # 函數映射
            return mapping(value)
    
    def _packet_to_dict(self, packet: Packet) -> Dict[str, Any]:
        """將 Packet 轉換為字典（用於後處理函數和 count_from lambda）"""
        result = {
            "序列號": packet.seq,
            "號誌控制器ID": packet.tc_id,
            "欄位長度": packet.length,
            "指令編號": packet.cmd_code,
        }
        if packet.command:
            result["指令"] = packet.command
        if packet.reply_type:
            result["訊息型態"] = packet.reply_type
        result["needs_ack"] = packet.needs_ack
        # 添加英文別名（用於 lambda）
        result["signal_count"] = packet.extra_fields.get("岔路數目", 0)
        result["sub_phase_count"] = packet.extra_fields.get("綠燈分相數目", 0)
        result.update(packet.extra_fields)
        return result
    


