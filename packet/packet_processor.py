"""
封包處理器
"""

import json
from config.log_setup import get_logger
from config.constants import CONTROL_STRATEGY_MAP
from utils import format_packet_display

class PacketProcessor:
    """封包處理器"""
    

    def __init__(self, packet_def, mode="receive"):
        self.logger = get_logger(f"tc.{mode}")
        self.mode = mode
        self.packet_def = packet_def
        # 命令到處理方法的映射
        self.handlers = {
            "5F00": self._handle_5f00, #主動回報
            "5F03": self._handle_5f03, #主動回報
            "5F0C": self._handle_5f0c, #主動回報
            "5F08": self._handle_5f08, #主動回報
            "5FC0": self._handle_5fc0, #查詢回報
            "5FC3": self._handle_5fc3, #查詢回報
            "5FC8": self._handle_5fc8, #查詢回報
            "5FC6": self._handle_5fc6, #查詢回報
            "0F04": self._handle_0f04,
            "0F80": self._handle_0f80,
            "0F81": self._handle_0f81,
        } 
        self.logger.info("封包處理器初始化完成")
    
    def _should_log(self, command):
        """判斷是否應該記錄日誌"""
        definition = self.packet_def.get_definition(command)
        return definition and self.mode in definition["log_modes"]

    def process(self, packet):
        """處理封包"""
        if not packet:
            return
        
        # 獲取命令碼
        command = packet.cmd_code

        # 查找對應的處理方法
        if command in self.handlers:
            # 調用 handler，handler 返回格式化後的日誌字符串
            log_message = self.handlers[command](packet)

            # 判斷是否記錄日誌
            if log_message and self._should_log(command):
                for line in log_message.split('\n'):
                    self.logger.info(line)
        
        elif self._should_log(command):
            # 沒有 handler，但需要記錄日誌時，記錄警告
            self.logger.warning(f"未找到處理器: {command}")
            self.logger.warning(f"封包內容: {packet}")

#=========5F群組封包處理=========

    def _handle_5f00(self, packet):
        """處理5F00封包（控制策略自動回報）"""
        control_strategy = packet.extra_fields.get("控制策略")
        begin_end = packet.extra_fields.get("控制策略狀態")
        
        fields = {
            "控制策略": control_strategy,
            "狀態": begin_end
        }
        
        return format_packet_display(packet, "5F00", fields)

    def _handle_5f03(self, packet):
        """處理5F03封包（時相資料庫管理）"""
        phase_order = packet.extra_fields.get("時相編號")
        signal_map = packet.extra_fields.get("號誌位置圖")  # SignalMap 對象
        signal_status_list = packet.extra_fields.get("燈號狀態列表")  # SignalStatusList 對象
    
        fields = {
            "時相編號": f"{phase_order:02X}",
            "號誌位置圖": str(signal_map),  # 自動格式化
            "岔路數目": packet.extra_fields.get("岔路數目"),
            "分相序號": packet.extra_fields.get("分相序號"),
            "步階序號": packet.extra_fields.get("步階序號"),
            "步階秒數": f"{packet.extra_fields.get('步階秒數')} 秒"
        }
        
        log_message = format_packet_display(packet, "5F03", fields)
        
        # 添加信號狀態
        if signal_status_list and len(signal_status_list) > 0:
            lines = log_message.split("\n")
            insert_pos = len(lines) - 1
            for status_line in reversed(signal_status_list.formatted_lines):
                lines.insert(insert_pos, status_line)
            log_message = "\n".join(lines)
        
        return log_message

    def _handle_5fc3(self, packet):
        """處理5FC3封包（時相排列回報）"""
        phase_order = packet.extra_fields.get("時相編號")
        signal_map = packet.extra_fields.get("號誌位置圖")
        signal_status_list = packet.extra_fields.get("燈號狀態列表")
        
        fields = {
            "時相編號": f"{phase_order:02X}",
            "號誌位置圖": str(signal_map),
            "岔路數目": packet.extra_fields.get("岔路數目"),
            "綠燈分相數目": packet.extra_fields.get("綠燈分相數目"),
        }
        
        log_message = format_packet_display(packet, "5FC3", fields)
        
        if signal_status_list and len(signal_status_list) > 0:
            lines = log_message.split("\n")
            insert_pos = len(lines) - 1
            for status_line in reversed(signal_status_list.formatted_lines):
                lines.insert(insert_pos, status_line)
            log_message = "\n".join(lines)
        
        return log_message

    def _handle_5f0c(self, packet):
        """處理5F0C封包（時相步階變換控制管理）"""
        control_strategy = packet.extra_fields.get("控制策略")
        sub_phase_id = packet.extra_fields.get("分相序號")
        step_id = packet.extra_fields.get("步階序號")
        

        
        fields = {
            "控制策略": control_strategy,
            "分相序號": sub_phase_id,
            "步階序號": step_id
        }
        
        return format_packet_display(packet, "5F0C", fields)
    
    def _handle_5fc0(self, packet):
        """處理5FC0封包（控制策略回報）"""
        control_strategy = packet.extra_fields.get("控制策略")
        effect_time = packet.extra_fields.get("動態控制策略有效時間")
        
        fields = {
            "控制策略": control_strategy,
            "有效時間": f"{effect_time} 分鐘"
        }
        
        return format_packet_display(packet, "5FC0", fields)

    def _handle_5f08(self, packet):
        """處理5F08封包（號誌控制器現場操作）"""
        operation = packet.extra_fields.get("現場操作碼")
        fields = {
            "現場操作碼": operation
        }
        return format_packet_display(packet, "5F08", fields)
    
    def _handle_5fc8(self, packet):
        """處理5FC8封包（時制計畫回報）"""
        plan_id = packet.extra_fields.get("時制計畫編號")
        direct = packet.extra_fields.get("基準方向")
        phase_order = packet.extra_fields.get("時相編號")
        sub_phase_count = packet.extra_fields.get("綠燈分相數")
        green_times = packet.extra_fields.get("各分相綠燈時間")
        cycle_time = packet.extra_fields.get("週期秒數")
        offset = packet.extra_fields.get("時差秒數")
        
        # 構建字段字典
        fields = {
            "時制計畫編號": plan_id,
            "基準方向": direct,
            "時相編號": f"{phase_order:02X}",
            "綠燈分相數": sub_phase_count,
        }
        
        # 添加各分相綠燈時間
        if isinstance(green_times, list) and green_times:
            for i, green_time in enumerate(green_times, 1):
                fields[f"分相 {i} 綠燈時間"] = f"{green_time} 秒"
        
        fields["週期秒數"] = f"{cycle_time} 秒"
        fields["時差秒數"] = f"{offset} 秒"
        
        return format_packet_display(packet, "5FC8", fields)

    def _handle_5fc6(self, packet):
        """處理5FC6封包（一般日時段型態查詢回報）"""
        segment_type = packet.extra_fields.get("時段類型")
        segment_count = packet.extra_fields.get("時段數量")
        segment_list = packet.extra_fields.get("時段列表")
        num_weekday = packet.extra_fields.get("星期數量")
        weekday_list = packet.extra_fields.get("星期列表")
        
        # 格式化時段列表為字符串列表
        formatted_segments = []
        if isinstance(segment_list, list):
            for i, segment in enumerate(segment_list, 1):
                formatted_segments.append(f"時段 {i}: {segment.hour:02d}:{segment.minute:02d} (計畫ID: {segment.plan_id})")
        
        # 格式化星期列表為字符串列表
        WEEKDAY_MAP = {
            1: "星期一", 2: "星期二", 3: "星期三", 4: "星期四",
            5: "星期五", 6: "星期六", 7: "星期日",
            11: "隔週休星期一", 12: "隔週休星期二", 13: "隔週休星期三",
            14: "隔週休星期四", 15: "隔週休星期五", 16: "隔週休星期六", 17: "隔週休星期日"
        }
        
        formatted_weekdays = []
        if isinstance(weekday_list, list):
            for weekday in weekday_list:
                weekday_name = WEEKDAY_MAP.get(weekday, f"未知({weekday})")
                formatted_weekdays.append(weekday_name)
        
        fields = {
            "時段類型": segment_type,
            "時段數量": segment_count,
            "時段列表": formatted_segments,  # 使用格式化後的列表
            "星期數量": num_weekday,
            "星期列表": formatted_weekdays,  # 使用格式化後的列表
        }
        
        return format_packet_display(packet, "5FC6", fields)


#=========0F群組封包處理=========

    def _handle_0f04(self, packet):
        """處理0F04封包（設備硬體狀態管理）"""
        hardware_status = packet.extra_fields.get("硬體狀態碼")
        hardware_status_list = packet.extra_fields.get("硬體狀態碼")  # 已經是格式化字符串列表
        
        # 使用 format_packet_display 格式化
        fields = {
            "硬體狀態碼": f"0x{hardware_status:04X}",
        }
        
        log_message = format_packet_display(packet, "0F04", fields)
        
        # 添加硬體狀態列表（如果已經是格式化字符串列表）
        if isinstance(hardware_status_list, list) and hardware_status_list:
            lines = log_message.split("\n")
            # 在 "原始資料" 之前插入
            insert_pos = len(lines) - 1
            for status_line in reversed(hardware_status_list):
                lines.insert(insert_pos, str(status_line))
            log_message = "\n".join(lines)
        
        return log_message

    def _handle_0f80(self, packet):
        """處理0F80封包（設定回報-成功）"""
        command_id = packet.extra_fields.get("指令ID")
        
        # 解析 command_id: 高字节是设备码，低字节是指令码
        device_code = (command_id >> 8) & 0xFF
        cmd_code = command_id & 0xFF
        cmd_code_str = f"{device_code:02X}{cmd_code:02X}"
        
        return format_packet_display(packet, "0F80", {
            "指令ID": cmd_code_str,
            "狀態": "設定成功"
        })

    def _handle_0f81(self, packet):
        """處理0F81封包（設定/查詢回報-失敗）"""
        command_id = packet.extra_fields.get("指令ID")
        error_code = packet.extra_fields.get("錯誤碼")
        param_num = packet.extra_fields.get("參數編號")
        
        # 解析 command_id
        device_code = (command_id >> 8) & 0xFF
        cmd_code = command_id & 0xFF
        cmd_code_str = f"{device_code:02X}{cmd_code:02X}"
        
        # 替換占位符(位置:xx)
        if param_num is not None:
            error_code = error_code.replace("{xx}", str(param_num))
        
        # 使用 format_packet_display 格式化
        fields = {
            "指令ID": cmd_code_str,
            "錯誤碼": error_code,
            "參數編號": param_num
        }
        
        return format_packet_display(packet, "0F81", fields)