"""
封包處理器
"""

import json
from config.log_setup import get_logger
from config.constants import CONTROL_STRATEGY_MAP
from utils import format_packet_display

class PacketProcessor:
    """封包處理器"""
    
    # 步階信息文件路徑
    STEP_INFO_FILE = 'logs/current_step.json'

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
        command = packet.get("指令編號")

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
        control_strategy = packet.get("控制策略")
        begin_end = packet.get("控制策略狀態")
        
        fields = {
            "控制策略": control_strategy,
            "狀態": begin_end
        }
        
        return format_packet_display(packet, "5F00", fields)

    def _handle_5f03(self, packet):
        """處理5F03封包（時相資料庫管理）"""
        phase_order = packet.get("時相編號")
        sub_phase_id = packet.get("分相序號")
        step_id = packet.get("步階序號")
        step_sec = packet.get("步階秒數")
        
        # 保存當前步階信息
        current_dict = {
            '分相序號': sub_phase_id,
            '步階序號': step_id,
            '步階秒數': step_sec,
            '時相編號': f'{phase_order:02X}'.upper()
        }

        try:
            with open(self.STEP_INFO_FILE, 'w') as file:
                json.dump(current_dict, file)
        except Exception as e:
            self.logger.error(f"保存步階信息失敗: {e}")
        
        signal_status_list = packet.get("燈號狀態列表")
        
        fields = {
            "時相編號": f"{phase_order:02X}",
            "號誌位置圖": packet.get("號誌位置圖"),
            "岔路數目": packet.get("岔路數目"),
            "分相序號": sub_phase_id,
            "步階序號": step_id,
            "步階秒數": f"{step_sec} 秒"
        }

        log_message = format_packet_display(packet, "5F03", fields)
    
        # 手動添加信號狀態（因為它們已經是格式化字符串）
        if isinstance(signal_status_list, list) and signal_status_list:
            lines = log_message.split("\n")
            # 在 "原始資料" 之前插入
            insert_pos = len(lines) - 1
            for status_line in reversed(signal_status_list):
                lines.insert(insert_pos, str(status_line))
            log_message = "\n".join(lines)
        
        return log_message

    def _handle_5fc3(self, packet):
        """處理5FC3封包（時相排列回報）"""
        phase_order = packet.get("時相編號")
        signal_map = packet.get("號誌位置圖")
        signal_count = packet.get("岔路數目")
        sub_phase_count = packet.get("綠燈分相數目")
        signal_status_list = packet.get("燈號狀態列表")
        
        # 構建字段字典
        fields = {
            "時相編號": f"{phase_order:02X}",
            "號誌位置圖": signal_map,
            "岔路數目": signal_count,
            "綠燈分相數目": sub_phase_count,
        }
        
        log_message = format_packet_display(packet, "5FC3", fields)
        
        # 添加信號狀態列表（如果已經是格式化字符串列表）
        if isinstance(signal_status_list, list) and signal_status_list:
            lines = log_message.split("\n")
            # 在 "原始資料" 之前插入
            insert_pos = len(lines) - 1
            for status_line in reversed(signal_status_list):
                lines.insert(insert_pos, str(status_line))
            log_message = "\n".join(lines)
        
        return log_message

    def _handle_5f0c(self, packet):
        """處理5F0C封包（時相步階變換控制管理）"""
        control_strategy = packet.get("控制策略")
        sub_phase_id = packet.get("分相序號")
        step_id = packet.get("步階序號")
        
        # 從 current_step.json 讀取步階秒數
        step_sec = self._load_step_sec()
        
        fields = {
            "控制策略": control_strategy,
            "分相序號": sub_phase_id,
            "步階序號": step_id,
            "步階秒數": f"{step_sec} 秒"
        }
        
        return format_packet_display(packet, "5F0C", fields)
    
    def _handle_5fc0(self, packet):
        """處理5FC0封包（控制策略回報）"""
        control_strategy = packet.get("控制策略")
        effect_time = packet.get("動態控制策略有效時間")
        
        fields = {
            "控制策略": control_strategy,
            "有效時間": f"{effect_time} 分鐘"
        }
        
        return format_packet_display(packet, "5FC0", fields)

    def _handle_5f08(self, packet):
        """處理5F08封包（號誌控制器現場操作）"""
        operation = packet.get("現場操作碼")
        fields = {
            "現場操作碼": operation
        }
        return format_packet_display(packet, "5F08", fields)
    
    def _handle_5fc8(self, packet):
        """處理5FC8封包（時制計畫回報）"""
        plan_id = packet.get("時制計畫編號")
        direct = packet.get("基準方向")
        phase_order = packet.get("時相編號")
        sub_phase_count = packet.get("綠燈分相數")
        green_times = packet.get("各分相綠燈時間")
        cycle_time = packet.get("週期秒數")
        offset = packet.get("時差秒數")
        
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


    def _load_step_sec(self):
        """讀取步階秒數（共享方法）"""
        try:
            with open(self.STEP_INFO_FILE, 'r') as f:
                step_data = json.load(f)
                return step_data.get('步階秒數')
        except Exception as e:
            self.logger.error(f"讀取步階秒數失敗: {e}")
            return 0


#=========0F群組封包處理=========

    def _handle_0f04(self, packet):
        """處理0F04封包（設備硬體狀態管理）"""
        hardware_status = packet.get("硬體狀態碼")
        hardware_status_list = packet.get("硬體狀態碼")  # 已經是格式化字符串列表
        
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
        command_id = packet.get("指令ID")
        
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
        command_id = packet.get("指令ID")
        error_code = packet.get("錯誤碼")
        param_num = packet.get("參數編號")
        
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