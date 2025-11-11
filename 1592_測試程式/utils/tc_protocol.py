"""
交通控制系統協議處理類
"""
import binascii
import datetime
import json
import struct
from .tc_core import *
from .log_setup import *

seq = 0

class TrafficControlProtocol:
    """交通控制協議處理"""
    
    def __init__(self, network=None):
        self.seq = 0
        self.buffer = bytearray()
        self.packet_handlers = self._register_handlers()
        self.network = network
        self.last_seq = 0
        self.tc_id = None
        self.f5f0c_callback = None

    def _register_handlers(self):
        """註冊封包處理器"""
        handlers = {}
        for cmd_code, cmd_info in COMMAND_REGISTRY.items():
            # 使用完整的指令碼作為鍵，避免 5FC0 和 0FC0 衝突
            handlers[cmd_code] = {
                "parser": getattr(self, cmd_info["parser"]),
                "processor": getattr(self, cmd_info["processor"]),
                "hex": cmd_info["hex"]
            }
        return handlers

    def calculate_checksum(self, data):
        """計算校驗和"""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    def escape_dle(self, data):
        """DLE 逸出處理"""
        result = bytearray()
        for byte in data:
            result.append(byte)
            if byte == DLE:
                result.append(DLE)
        return result

    def unescape_dle(self, data):
        """DLE 反逸出處理（解析時使用）"""
        result = bytearray()
        i = 0
        while i < len(data):
            if data[i] == DLE and i + 1 < len(data) and data[i + 1] == DLE:
                # 遇到連續兩個 DLE，只保留一個
                result.append(DLE)
                i += 2  # 跳過下一個 DLE
            else:
                result.append(data[i])
                i += 1
        return result

    def get_seq(self):
        global seq
        if seq < 254:
            seq += 1
        else:
            seq = 0
        return seq

    def next_seq(self):
        """取得下一個序列號"""
        self.seq = (self.seq + 1) & 0xFF
        return self.seq

    def create_ack_packet(self, seq, tc_id):
        """建立 ACK 確認封包"""
        try:
            # ACK 封包格式：DLE + DD + SEQ + ADDR_HIGH + ADDR_LOW + LEN_HIGH + LEN_LOW + CKS
            addr_high = (tc_id >> 8) & 0xFF
            addr_low = tc_id & 0xFF
            length = 8  # ACK 封包固定長度

            # 建立 ACK 封包內容
            ack_data = bytearray([
                DLE,         # 0xAA
                ACK,         # 0xDD 
                seq,         # 序列號
                addr_high,   # 地址高位
                addr_low,    # 地址低位  
                0x00,        # 長度高位
                0x08         # 長度低位 (固定8)
            ])

            # 計算校驗和
            cks = self.calculate_checksum(ack_data)
            ack_data.append(cks)

            return bytes(ack_data)

        except Exception as e:
            log_error(f"建立 ACK 封包失敗: {e}")
            return None

    def parse_buffer(self, data):
        """從資料緩衝區解析封包"""
        packets = []
        remaining_data = self.unescape_dle(data)
        
        while len(remaining_data) >= 9:
            # 尋找封包開頭
            start_idx = -1
            for i in range(len(remaining_data) - 1):
                if remaining_data[i] == DLE and remaining_data[i+1] == STX:
                    start_idx = i
                    break
            
            if start_idx == -1:
                break
            
            if start_idx > 0:
                remaining_data = remaining_data[start_idx:]
            
            if len(remaining_data) < 7:
                break
            
            length = (remaining_data[5] << 8) | remaining_data[6]
            
            # 尋找封包結尾
            dle_etx_idx = -1
            for i in range(7, len(remaining_data) - 1):
                if remaining_data[i] == DLE and remaining_data[i+1] == ETX:
                    dle_etx_idx = i
                    break
            
            if dle_etx_idx == -1 or dle_etx_idx + 2 >= len(remaining_data):
                break

            packet_data = remaining_data[:dle_etx_idx + 3]
            remaining_data = remaining_data[dle_etx_idx + 3:]

            if len(packet_data) > 8:
                command_prefix = packet_data[7]
                command_suffix = packet_data[8]
                
                # 構建完整的指令碼
                if command_prefix == 0x5F:
                    command_code = f"5F{command_suffix:02X}"
                elif command_prefix == 0x0F:
                    command_code = f"0F{command_suffix:02X}"
                else:
                    #log_info(f"接收到未知的指令: {binascii.hexlify(packet_data).decode('ascii')}")
                    continue
                
                # 使用註冊的處理器
                if command_code in self.packet_handlers:
                    parser = self.packet_handlers[command_code]["parser"]
                    result = parser(packet_data)
                    if result:
                        packets.append(result)
                # else:
                #     log_info(f"接收到未知的{command_code}指令: {binascii.hexlify(packet_data).decode('ascii')}")

        return packets, remaining_data

    def process_packet(self, packet):
        """封包處理入口"""
        if not packet:
            return

        command = packet.get("command", "Unknown")
        command_info = None

        for cmd_code, cmd_data in COMMAND_REGISTRY.items():
            if cmd_code == command:
                command_info = cmd_data
                break

        if command_info:
            processor = getattr(self, command_info["processor"])
            processor(packet)
            
            if self.network:
                seq = packet.get("seq")
                tc_id = packet.get("tc_id")
                if seq is not None and tc_id is not None:
                    ack_packet = self.create_ack_packet(seq, tc_id)
                    if ack_packet:
                        log_info(f"回傳 ACK 封包 (Seq: {seq}, TC_ID: {tc_id})")
                        self.network.send_packet(ack_packet)

        else:
            log_warning(f"收到未知命令封包: {command}")

    def addAA(self, command):
        _command = bytearray()
        for i in command:
            if i == 0xAA:
                _command.append(i)
                _command.append(i)
            else:
                _command.append(i)

        return bytes(_command)

    def cks(self, command):
        cks = 0
        for i in range(len(command)):
            cks =cks ^ command[i]
        return cks.to_bytes(1, 'big')

    #|<--------------------------------------------- 解析 --------------------------------------------->|
    def parse_0f04_packet(self, data):
        """解析 0F04 系統狀態回報封包"""
        try:
            log_info(f"接收 0F04 封包: {binascii.hexlify(data).decode('ascii')}")
            seq = data[2]
            addr = (data[3] << 8) | data[4]
            length = (data[5] << 8) | data[6]
            
            # 0F04 封包格式: 0F 04 [狀態碼高位] [狀態碼低位]
            if len(data) >= 11:
                status_high = data[9]
                status_low = data[10]
                system_status = (status_high << 8) | status_low
            else:
                system_status = 0
            
            # 狀態碼解析
            status_descriptions = {
                0x4100: "系統正常運行",
                0x4200: "系統警告狀態", 
                0x4300: "系統異常狀態",
                0x0000: "未知狀態"
            }
            
            status_description = status_descriptions.get(system_status, f"未定義狀態(0x{system_status:04X})")
            
            return {
                "seq": seq, "addr": addr, "tc_id": addr, "length": length,
                "command": "0F04", "system_status": system_status,
                "status_description": status_description,
                "raw_data": binascii.hexlify(data).decode('ascii'),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            log_error(f"解析 0F04 封包失敗: {e}")
            return None

    def parse_0f80_packet(self, data):
        """解析 0F80 成功回應封包"""
        try:
            log_info(f"接收 0F80 封包: {binascii.hexlify(data).decode('ascii')}")
            seq = data[2]
            addr = (data[3] << 8) | data[4]
            length = (data[5] << 8) | data[6]

            # 0F80 封包格式: 0F 80 [CommandID高位] [CommandID低位]
            if len(data) >= 11:
                command_id_high = data[9]
                command_id_low = data[10]
                command_id = (command_id_high << 8) | command_id_low
            else:
                command_id = 0
            
            return {
                "seq": seq, "addr": addr, "tc_id": addr, "length": length,
                "command": "0F80", "command_id": command_id,
                "raw_data": binascii.hexlify(data).decode('ascii'),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            log_error(f"解析 0F80 封包失敗: {e}")
            return None

    def parse_0f81_packet(self, data):
        """解析 0F81 失敗回應封包"""
        try:
            log_info(f"接收 0F81 封包: {binascii.hexlify(data).decode('ascii')}")
            seq = data[2]
            addr = (data[3] << 8) | data[4]
            length = (data[5] << 8) | data[6]
            
            # 0F81 封包格式: 0F 81 [CommandID高位] [CommandID低位] [ErrorCode] [ParameterNumber]
            command_id_high = data[9] if len(data) > 9 else 0
            command_id_low = data[10] if len(data) > 10 else 0
            command_id = (command_id_high << 8) | command_id_low
            
            error_code = data[11] if len(data) > 11 else 0
            parameter_number = data[12] if len(data) > 12 else 0
            
            return {
                "seq": seq, "addr": addr, "tc_id": addr, "length": length,
                "command": "0F81", "command_id": command_id,
                "error_code": error_code, "parameter_number": parameter_number,
                "raw_data": binascii.hexlify(data).decode('ascii'),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            log_error(f"解析 0F81 封包失敗: {e}")
            return None

    def parse_5f08_packet(self, data):
        log_info(f"接收 5F08 封包: {binascii.hexlify(data).decode('ascii')}")
        seq = data[2]
        addr = (data[3] << 8) | data[4]
        length = (data[5] << 8) | data[6]

        field_operate = hex(data[9])

        return {
            "seq": seq, "addr": addr, "tc_id": addr, "length": length,
            "command": "5F08", "field_operate": field_operate,
            "raw_data": binascii.hexlify(data).decode('ascii'),
            "timestamp": datetime.datetime.now().isoformat()
        }

    def parse_5f10_packet(self, data):
        """解析 5F10 控制策略設定封包"""
        log_info(f"接收 5F10 封包: {binascii.hexlify(data).decode('ascii')}")
        seq = data[2]
        addr = (data[3] << 8) | data[4]
        length = (data[5] << 8) | data[6]
        
        control_strategy = data[9] if len(data) > 9 else 0
        effect_time = data[10] if len(data) > 10 else 0
        
        # 解析控制策略位元
        strategy_details = {
            "fixed_time": bool(control_strategy & 0x01),      # Bit 0
            "dynamic": bool(control_strategy & 0x02),         # Bit 1  
            "intersection_manual": bool(control_strategy & 0x04), # Bit 2
            "central_manual": bool(control_strategy & 0x08),  # Bit 3
            "phase_control": bool(control_strategy & 0x10),   # Bit 4
            "immediate_control": bool(control_strategy & 0x20), # Bit 5 
            "actuated": bool(control_strategy & 0x40),        # Bit 6
            "special_route": bool(control_strategy & 0x80),   # Bit 7
        }
        
        return {
            "seq": seq, "addr": addr, "tc_id": addr, "length": length,
            "command": "5F10", "control_strategy": control_strategy,
            "control_strategy_details": strategy_details,
            "effect_time": effect_time,
            "raw_data": binascii.hexlify(data).decode('ascii'),
            "timestamp": datetime.datetime.now().isoformat()
        }

    def parse_5f40_packet(self, data):
        """解析 5F40 查詢控制策略封包"""
        log_info(f"接收 5F40 封包: {binascii.hexlify(data).decode('ascii')}")
        seq = data[2]
        addr = (data[3] << 8) | data[4]
        length = (data[5] << 8) | data[6]
        
        return {
            "seq": seq, "addr": addr, "tc_id": addr, "length": length,
            "command": "5F40",
            "raw_data": binascii.hexlify(data).decode('ascii'),
            "timestamp": datetime.datetime.now().isoformat()
        }

    def parse_5f03_packet(self, data):
        """解析 5F03 號誌控制封包"""
        log_info(f"接收 5F03 封包: {binascii.hexlify(data).decode('ascii')}")
        seq = data[2]
        addr = (data[3] << 8) | data[4]
        length = (data[5] << 8) | data[6]

        phase_order = data[9]
        signal_map = data[10]
        signal_count = data[11]
        sub_phase_id = data[12]
        step_id = data[13]
        step_sec = (data[14] << 8) | data[15]

        signal_status = []
        for i in range(signal_count):
            if 16 + i < len(data):
                signal_status.append(data[16 + i])

        signal_map_list = int_to_binary_list(signal_map)
        signal_status_details = []

        for status in signal_status:
            status_list = int_to_binary_list(status)

            # 提取原始位元
            pedgreen_bit = status_list[6] if len(status_list) > 6 else 0
            pedred_bit = status_list[7] if len(status_list) > 7 else 0

            # 判斷行人燈狀態邏輯
            if pedgreen_bit and pedred_bit:
                pedgreen = 0
                pedred = 0
                pedgreenflash = 1
            else:
                # 正常狀態
                pedgreen = pedgreen_bit
                pedred = pedred_bit
                pedgreenflash = 0

            status_dict = {
                "allred": status_list[0] if len(status_list) > 0 else 0,
                "yellow": status_list[1] if len(status_list) > 1 else 0,
                "green": status_list[2] if len(status_list) > 2 else 0,
                "turnleft": status_list[3] if len(status_list) > 3 else 0,
                "straight": status_list[4] if len(status_list) > 4 else 0,
                "turnright": status_list[5] if len(status_list) > 5 else 0,
                "pedgreen": pedgreen,
                "pedred": pedred,
                "pedgreenflash": pedgreenflash,
            }
            signal_status_details.append(status_dict)

        return {
            "seq": seq, "addr": addr, "tc_id": addr, "length": length,
            "command": "5F03", "phase_order": phase_order, "signal_map": signal_map,
            "signal_map_list": signal_map_list, "signal_count": signal_count,
            "sub_phase_id": sub_phase_id, "step_id": step_id, "step_sec": step_sec,
            "signal_status": signal_status, "signal_status_details": signal_status_details,
            "raw_data": binascii.hexlify(data).decode('ascii'),
            "timestamp": datetime.datetime.now().isoformat()
        }

    def parse_5fc6_packet(self, data):
        """
        解析 5FC6 一般日時段型態查詢回報封包
        格式: 5F H+C6 H + SegmentType + SegmentCount + (Hour+Min+PlanID)*(SegmentCount) + NumWeekDay + WeekDay*(NumWeekDay)
        """
        try:
            log_info(f"接收 5FC6 封包: {binascii.hexlify(data).decode('ascii')}")
            seq = data[2]
            addr = (data[3] << 8) | data[4]
            length = (data[5] << 8) | data[6]
            
            segment_type = data[9]
            segment_count = data[10]
            offset = 11
            segment_list = []
            for i in range(segment_count):
                if offset+2 >= len(data):
                    break
                hour = data[offset]
                minute = data[offset+1]
                plan_id = data[offset+2]
                segment_list.append({'hour': hour, 'minute': minute, 'plan_id': plan_id})
                offset += 3
            if offset >= len(data):
                num_weekday = 0
                weekday_list = []
            else:
                num_weekday = data[offset]
                offset += 1
                weekday_list = []
                for i in range(num_weekday):
                    if offset >= len(data):
                        break
                    weekday_list.append(data[offset])
                    offset += 1
            return {
                'seq': seq,
                'addr': addr,
                'tc_id': addr,
                'length': length,
                'command': '5FC6',
                'segment_type': segment_type,
                'segment_count': segment_count,
                'segment_list': segment_list,
                'num_weekday': num_weekday,
                'weekday_list': weekday_list,
                'raw_data': binascii.hexlify(data).decode('ascii'),
                'timestamp': datetime.datetime.now().isoformat()
            }
        except Exception as e:
            log_error(f"解析 5FC6 封包失敗: {e}")
            return None

    def parse_5fc0_packet(self, data):
        """解析 5FC0 控制策略回報封包"""
        try:
            log_info(f"接收 5FC0 封包: {binascii.hexlify(data).decode('ascii')}")
            seq = data[2]
            addr = (data[3] << 8) | data[4]
            length = (data[5] << 8) | data[6]

            # 檢查封包長度
            if len(data) < 11:
                log_error(f"5FC0 封包長度不足: {len(data)} < 11")
                return None

            control_strategy = data[9]
            effect_time = data[10]

            control_strategy_details = {
                "fixed_time": bool(control_strategy & CS_FIXED_TIME),
                "dynamic": bool(control_strategy & CS_DYNAMIC),
                "intersection_manual": bool(control_strategy & CS_INTERSECTION_MANUAL),
                "central_manual": bool(control_strategy & CS_CENTRAL_MANUAL),
                "phase_control": bool(control_strategy & CS_PHASE_CONTROL),
                "immediate_control": bool(control_strategy & CS_IMMEDIATE_CONTROL),
                "actuated": bool(control_strategy & CS_ACTUATED),
                "special_route": bool(control_strategy & CS_SPECIAL_ROUTE),
            }

            log_info(f"解析 5FC0 封包: 策略=0x{control_strategy:02X}, 時間= {effect_time} 分鐘有效")

            return {
                "seq": seq, "addr": addr, "tc_id": addr, "length": length,
                "command": "5FC0", "control_strategy": control_strategy,
                "control_strategy_details": control_strategy_details,
                "effect_time": effect_time,
                "raw_data": binascii.hexlify(data).decode('ascii'),
                "timestamp": datetime.datetime.now().isoformat()
            }

        except Exception as e:
            log_error(f"解析 5FC0 封包失敗: {e}")
            return None

    def parse_0fc0_packet(self, data):
        """解析 0FC0 查詢現場設備編號回報封包"""
        try:
            log_info(f"接收 0F02 封包: {binascii.hexlify(data).decode('ascii')}")
            seq = data[2]
            addr = (data[3] << 8) | data[4]
            length = (data[5] << 8) | data[6]
            
            equipment_no = data[9]      # 0x00
            sub_count = data[10]        # 0x01
            sub_equipment_no = data[11] # 0x00
            
            if len(data) > 12:
                equipment_id = data[12]
            else:
                equipment_id = 0

        except Exception as e:
            log_error(f"解析 0FC0 封包失敗: {e}")
            return None

        return {
            "seq": seq, "addr": addr, "tc_id": addr, "length": length,
            "command": "0FC0", "equipment_no": equipment_no, "sub_count": sub_count, 
            "sub_equipment_no": sub_equipment_no, "equipment_id": equipment_id, 
            "raw_data": binascii.hexlify(data).decode('ascii'),
            "timestamp": datetime.datetime.now().isoformat()
        }

    def parse_0f02_packet(self, data):
        """解析 0F02 回報終端設備現場手動更改時間封包"""
        try:
            log_info(f"接收 0F02 封包: {binascii.hexlify(data).decode('ascii')}")
            seq = data[2]
            addr = (data[3] << 8) | data[4]
            length = (data[5] << 8) | data[6]
        except Exception as e:
            log_error(f"解析 0F02 封包失敗: {e}")
            return None
        
        return {
            "seq": seq, "addr": addr, "tc_id": addr, "length": length,
            "command": "0F02", "raw_data": binascii.hexlify(data).decode('ascii'),
            "timestamp": datetime.datetime.now().isoformat()
        }

    def parse_5f0c_packet(self, data):
        """解析 5F0C 時相步階變換回報封包"""
        try:
            log_info(f"接收 5F0C 封包: {binascii.hexlify(data).decode('ascii')}")
            seq = data[2]
            addr = (data[3] << 8) | data[4]
            length = (data[5] << 8) | data[6]

            # 5F0C 封包格式: 5F 0C [ControlStrategy] [SubPhaseID] [StepID]
            if len(data) >= 12:
                control_strategy = data[9]
                sub_phase_id = data[10]
                step_id = data[11]
            else:
                control_strategy = 0
                sub_phase_id = 0
                step_id = 0

            # 解析控制策略位元 (可以重用 5F10 的解析邏輯)
            control_strategy_details = {
                "fixed_time": bool(control_strategy & CS_FIXED_TIME),
                "dynamic": bool(control_strategy & CS_DYNAMIC),
                "intersection_manual": bool(control_strategy & CS_INTERSECTION_MANUAL),
                "central_manual": bool(control_strategy & CS_CENTRAL_MANUAL),
                "phase_control": bool(control_strategy & CS_PHASE_CONTROL),
                "immediate_control": bool(control_strategy & CS_IMMEDIATE_CONTROL),
                "actuated": bool(control_strategy & CS_ACTUATED),
                "special_route": bool(control_strategy & CS_SPECIAL_ROUTE),
            }

            return {
                "seq": seq, "addr": addr, "tc_id": addr, "length": length,
                "command": "5F0C", "control_strategy": control_strategy,
                "control_strategy_details": control_strategy_details,
                "sub_phase_id": sub_phase_id,
                "step_id": step_id,
                "raw_data": binascii.hexlify(data).decode('ascii'),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            log_error(f"解析 5F0C 封包失敗: {e}")
            return None

    def parse_5fc8_packet(self, data):
        """解析 5FC8 查詢回報封包 - 回報目前時制計畫內容"""
        try:
            log_info(f"接收 5FC8 封包: {binascii.hexlify(data).decode('ascii')}")
            seq = data[2]
            addr = (data[3] << 8) | data[4]
            length = (data[5] << 8) | data[6]
            
            # 檢查封包最小長度 (DLE+STX+SEQ+ADDR+CMD+PARAMS+CHECKSUM)
            if len(data) < 11:
                log_error(f"5FC8 封包長度不足: {len(data)} < 11")
                return None
            
            # 5FC8 封包格式: 5F H + C8 H + PlanID + Direct + PhaseOrder + SubPhaseCount + Green(SubPhaseCount) + CycleTime + Offset
            offset = 9  # 從指令碼後開始解析
            
            # PlanID (假設 1 byte，因為沒有 5F14H 的詳細規格)
            plan_id = data[offset] if offset < len(data) else 0
            offset += 1
            
            # Direct (假設 1 byte，因為沒有 5F11H 的詳細規格)
            direct = data[offset] if offset < len(data) else 0
            offset += 1
            
            # PhaseOrder (假設 1 byte，因為沒有 5F13H 的詳細規格)
            phase_order = data[offset] if offset < len(data) else 0
            offset += 1
            
            # SubPhaseCount (1 byte, 1-8)
            sub_phase_count = data[offset] if offset < len(data) else 0
            offset += 1
            
            # Green(SubPhaseCount) - 每個分相 2 bytes
            green_times = []
            for i in range(sub_phase_count):
                if offset + 1 < len(data):
                    green_time = (data[offset] << 8) | data[offset + 1]
                    green_times.append(green_time)
                    offset += 2
                else:
                    green_times.append(0)
            
            # CycleTime (2 bytes)
            cycle_time = 0
            if offset + 1 < len(data):
                cycle_time = (data[offset] << 8) | data[offset + 1]
                offset += 2
            
            # Offset (2 bytes)
            offset_time = 0
            if offset + 1 < len(data):
                offset_time = (data[offset] << 8) | data[offset + 1]
            
            return {
                "seq": seq, "addr": addr, "tc_id": addr, "length": length,
                "command": "5FC8",
                "plan_id": plan_id,
                "direct": direct,
                "phase_order": phase_order,
                "sub_phase_count": sub_phase_count,
                "green_times": green_times,
                "cycle_time": cycle_time,
                "offset": offset_time,
                "raw_data": binascii.hexlify(data).decode('ascii'),
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            log_error(f"解析 5FC8 封包失敗: {e}")
            return None

    #|<--------------------------------------------- 處理 --------------------------------------------->|
    def process_0f04_packet(self, packet):
        """處理 0F04 系統狀態回報封包"""
        tc_id = packet.get("tc_id", 0)
        system_status = packet.get("system_status", 0)
        status_description = packet.get("status_description", "未知")
        
        log_info(f"TC{tc_id:03d} 系統狀態回報: {status_description} (0x{system_status:04X})")

    def process_0f80_packet(self, packet):
        """處理 0F80 成功回應封包"""
        tc_id = packet.get("tc_id", 0)
        command_id = packet.get("command_id", 0)
        original_command = packet.get("command", "") # 獲取原始命令碼，可能是 0F80 或 5F80

        '''
        只記錄針對 5F40, 5F10, 5F1C 指令的成功回報
        考慮交通控制器可能回傳 0x0101 作為成功回覆
        暫時記錄所有 0F80 的 Command ID 以便除錯
        '''
        if command_id in [0x5F40, 0x5F10, 0x5F1C] or (original_command == "5F80" and command_id == 0x0101):
            log_info(f"TC{tc_id:03d} 指令下傳成功: 0x{command_id:04X}") # 暫時記錄所有 0F80 Command ID

    def process_0f81_packet(self, packet):
        """處理 0F81 失敗回應封包"""
        tc_id = packet.get("tc_id", 0)
        command_id = packet.get("command_id", 0)
        error_code = packet.get("error_code", 0)
        parameter_number = packet.get("parameter_number", 0)
        
        # 錯誤代碼對照表
        error_descriptions = {
            0x01: "無此指令",
            0x02: "參數範圍錯誤", 
            0x04: "位元順序錯誤",
            0x08: "設備關列錯誤",
            0x10: "忙碌中",
            0x20: "資料內容錯誤",
            0x40: "參數個數超過實體限制",
            0x80: "無此項號或實體不存在"
        }

        error_desc = error_descriptions.get(error_code, f"未知錯誤(0x{error_code:02X})")

        log_info(f"TC{tc_id:03d} 指令執行失敗")
        log_info(f"回應指令ID: 0x{command_id:04X}")
        log_info(f"錯誤代碼: 0x{error_code:02X} - {error_desc}")
        log_info(f"參數編號: {parameter_number}")

    def process_5f08_packet(self, packet):
        tc_id = packet.get("tc_id", 0)
        field_operate = packet.get("field_operate", 0)
        
        mapping_dict = {
            "0x80": "上次現場操作回復",
            "0x40": "現場閃光",
            "0x02": "現場全紅",
            "0x01": "現場手動"
        }
        field_operate_status = mapping_dict.get(str(field_operate), 0)

        # log_info(f"號誌控制器 TC{tc_id:03d} - 現場操作狀態: {field_operate_status}")

    def process_5f10_packet(self, packet):
        """處理 5F10 控制策略設定封包"""
        tc_id = packet.get("tc_id", 0)
        strategy_details = packet.get("control_strategy_details", {})
        effect_time = packet.get("effect_time", 0)
        
        if strategy_details:
            log_info(f"TC{tc_id:03d} 控制策略切換, 有效時間={effect_time}分鐘")
        else:
            strategy_desc = get_control_strategy_desc(strategy_details)
            log_info(f"TC{tc_id:03d} 控制策略變更: {strategy_desc}, 有效時間={effect_time}分鐘")

    def process_5f40_packet(self, packet):
        """處理 5F40 查詢控制策略封包"""
        tc_id = packet.get("tc_id", 0)
        log_info(f"TC{tc_id:03d} 收到查詢控制策略指令")

    def process_5f03_packet(self, packet):
        """處理 5F03 號誌控制封包 (按規格輸出)"""
        tc_id = packet.get("tc_id", 0)
        phase_order = packet.get("phase_order", 0)
        sub_phase_id = packet.get("sub_phase_id", 0)
        step_id = packet.get("step_id", 0)
        step_sec = packet.get("step_sec", 0)
        signal_count = packet.get("signal_count", 0)

        current_dict = {
            'sub_phase_id': sub_phase_id,
            'step_id': step_id,
            'step_sec': step_sec,
            'phase_order': f'{phase_order:02X}'.upper()
        }

        with open('logs/current_step.json', 'w') as file:
            json.dump(current_dict, file)

        print_packet_info(packet)
        # log_info(f"號誌控制器 TC{tc_id:03d} - 時相: {f'{phase_order:02X}'.upper()} | 步階: {sub_phase_id}-{step_id} | 秒數: {step_sec} 秒. ")

    def process_5fc0_packet(self, packet):
        """處理 5FC0 控制策略回報封包"""
        tc_id = packet.get("tc_id", 0)
        strategy_details = packet.get("control_strategy_details", {})
        effect_time = packet.get("effect_time", 0)
        control_strategy = packet.get("control_strategy", 0)

        strategy_desc = get_control_strategy_desc(strategy_details)
        log_info(f"控制策略回報 TC{tc_id:03d}: {strategy_desc}, 有效時間= {effect_time} 分鐘")
        log_info(f"策略代碼: 0x{control_strategy:02X}")

    def process_5fc6_packet(self, packet):
        """
        處理 5FC6 一般日時段型態查詢回報封包
        """
        tc_id = packet.get('tc_id', 0)
        segment_type = packet.get('segment_type', 0)
        segment_count = packet.get('segment_count', 0)
        segment_list = packet.get('segment_list', [])
        num_weekday = packet.get('num_weekday', 0)
        weekday_list = packet.get('weekday_list', [])
        log_info(f"TC{tc_id:03d} 5FC6查詢回報: SegmentType={segment_type}, SegmentCount={segment_count}, NumWeekDay={num_weekday}, WeekDay={weekday_list}")
        for idx, seg in enumerate(segment_list):
            log_info(f"  時段{idx+1}: {seg['hour']:02d}:{seg['minute']:02d} 計畫ID={seg['plan_id']}")

    def process_0fc0_packet(self, packet):
        """處理 0FC0 查詢現場設備編號回報封包"""
        tc_id = packet.get('tc_id', 0)
        equipment_no = packet.get('equipment_no')
        sub_count = 0 if equipment_no == 0 else packet.get('sub_count')
        sub_equipment_no = packet.get('sub_equipment_no')
        equipment_id = packet.get('equipment_id')
        log_info(f"TC{tc_id:03d} 查詢現場設備編號回報: 子路序號={equipment_no}, 子路設備數目={sub_count}, 子路設備序號={sub_equipment_no}, 設備編號={equipment_id}")

    def process_0f02_packet(self, packet):
        """處理 0F02 回報終端設備現場手動更改時間封包"""
        tc_id = packet.get('tc_id', 0)
        log_info(f"TC{tc_id:03d} 回報終端設備現場手動更改時間")

    def process_5f0c_packet(self, packet):
        """處理 5F0C 時相步階變換回報封包"""
        tc_id = packet.get("tc_id", 0)
        sub_phase_id = packet.get("sub_phase_id", 0)
        step_id = packet.get("step_id", 0)
        control_strategy = packet.get("control_strategy", 0)
        strategy_details = packet.get("control_strategy_details", {})
        strategy_desc = get_control_strategy_desc(strategy_details)

        # 從 current_step.json 讀取 step_sec
        try:
            with open('logs/current_step.json', 'r') as f:
                step_data = json.load(f)
                step_sec = step_data.get('step_sec', 0)
        except Exception as e:
            log_error(f"讀取 step_sec 失敗: {e}")
            step_sec = 0

        log_info(f"TC{tc_id:03d} 時相步階變換 5F0C: 當前策略={strategy_desc} (0x{control_strategy:02X}), 時相={sub_phase_id}, 步階={step_id}")

        # Check if callback is set and call it
        if self.f5f0c_callback:
            self.f5f0c_callback(tc_id, sub_phase_id, step_id, step_sec)

    def process_5fc8_packet(self, packet):
        """處理 5FC8 查詢回報封包 - 回報目前時制計畫內容"""
        tc_id = packet.get("tc_id", 0)
        plan_id = packet.get("plan_id", 0)
        direct = packet.get("direct", 0)
        phase_order = packet.get("phase_order", 0)
        sub_phase_count = packet.get("sub_phase_count", 0)
        green_times = packet.get("green_times", [])
        cycle_time = packet.get("cycle_time", 0)
        offset_time = packet.get("offset", 0)
        
        log_info(f"TC{tc_id:03d} 回報目前時制計畫內容:")
        log_info(f"  時制計畫編號 (PlanID): {plan_id}")
        log_info(f"  基準方向 (Direct): {direct}")
        log_info(f"  時相種類編號 (PhaseOrder): {phase_order}")
        log_info(f"  綠燈分相數 (SubPhaseCount): {sub_phase_count}")
        log_info(f"  週期秒數 (CycleTime): {cycle_time} 秒")
        log_info(f"  時差秒數 (Offset): {offset_time} 秒")
        
        # 顯示各分相的綠燈時間
        if green_times:
            log_info(f"  各分相綠燈時間:")
            for i, green_time in enumerate(green_times):
                log_info(f"    分相 {i+1}: {green_time} 秒")
        else:
            log_info(f"  綠燈時間資料: 無資料")


    #|<--------------------------------------------- 建立 --------------------------------------------->|
    def create_5f16_packet(self, tc_id, segment_info):
        """
        產生 5F16 設定封包
        """
        segmentType = segment_info['segmentType']
        segmentCount = segment_info['segmentCount']
        numWeekDay = segment_info['numWeekDay']
        weekDayList = segment_info['weekDay']
        segmentList = []
        for segment in segment_info['beginTime']:
            segmentTimeCut = segment['time'].split(':')
            segmentList.append(int(segmentTimeCut[0]))
            segmentList.append(int(segmentTimeCut[1]))
            segmentList.append(segment['planId'])
        command = self._command5F16(tc_id, segmentType, segmentCount, segmentList, numWeekDay, weekDayList)
        return command

    def _command5F16(self, tc_id, segmentType, segmentCount, segmentList, numWeekDay, weekDayList):
        '''
        設定一般日時段型態
        '''
        seq = self.next_seq()
        # seq = self.get_seq()
        addr = int(tc_id)
        commandLength = 15 + segmentCount * 3 + numWeekDay
        packFormat = '>BBBB' + 'BBB' * segmentCount + 'B' + 'B' * numWeekDay

        info = struct.pack(packFormat, 0x5F, 0x16, segmentType, segmentCount, *segmentList, numWeekDay, *weekDayList)
        if info.count(0xAA) > 0:
            info = self.addAA(info)
            commandLength = 10 + len(info)
            header = struct.pack('>BBBHH',0xAA,0xBB,seq,addr,commandLength)
        else:
            header = struct.pack('>BBBHH',0xAA,0xBB,seq,addr,commandLength)
        footer = struct.pack('>BB',0xAA,0xCC)
        _cks = self.cks(header + info + footer)

        return header + info + footer + _cks

    def create_5f46_packet(self, tc_id, segment_info):
        """
        產生 5F46 查詢封包
        """
        segmentType = segment_info['segmentType']
        weekDayList = segment_info['weekDay']
        command = self._command5F46(tc_id, segmentType, weekDayList)
        return command

    def _command5F46(self, addr, segmentType, weekDayList):
        '''
        查詢一般日時段型態之設定內容。
        '''
        seq = self.next_seq()
        #seq = self.get_seq()
        commandLength = 13 + len(weekDayList)
        packFormat = '>BBB' + 'B'*len(weekDayList)
        info = struct.pack(packFormat,0x5F,0x46,segmentType,*weekDayList)

        if info.count(0xAA) > 0:
            info = self.addAA(info)
            commandLength = 10 + len(info)
            header = struct.pack('>BBBHH',0xAA,0xBB,seq,addr,commandLength)
        else:
            header = struct.pack('>BBBHH',0xAA,0xBB,seq,addr,commandLength)
        footer = struct.pack('>BB',0xAA,0xCC)
        _cks = self.cks(header + info + footer)

        return header + info + footer + _cks

    def create_0f40_packet(self, tc_id, equipment_no):
        """
        產生 0F40 查詢封包
        """
        command = self._command0F40(tc_id, equipment_no)
        return command

    def _command0F40(self, addr, EquipmentNo):
        '''
        查詢現場設備編號
        '''
        seq = self.next_seq()
        commandLength = 13
        info = struct.pack('>BBB',0x0F,0x40,EquipmentNo)

        if info.count(0xAA) > 0:
            info = self.addAA(info)
            commandLength = 10 + len(info)
            header = struct.pack('>BBBHH',0xAA,0xBB,seq,addr,commandLength)
        else:
            header = struct.pack('>BBBHH',0xAA,0xBB,seq,addr,commandLength)
        footer = struct.pack('>BB',0xAA,0xCC)
        _cks = self.cks(header + info + footer)

        return header + info + footer + _cks

    def create_5f10_packet(self, tc_id, control_strategy, effect_time):
        """
        產生 5F10 控制策略設定封包
        """
        self.seq = (self.seq + 1) & 0xFF
        seq = self.seq
        addr = int(tc_id)
        info = struct.pack('>BBBB', 0x5F, 0x10, control_strategy, effect_time)
        escaped_info = self.escape_dle(info)
        commandLength = 10 + len(escaped_info)
        header = struct.pack('>BBBHH', 0xAA, 0xBB, seq, addr, commandLength)
        footer = struct.pack('>BB', 0xAA, 0xCC)
        cks = 0
        for b in header + info + footer:
            cks ^= b
        return header + info + footer + bytes([cks])

    def create_5f40_packet(self, tc_id):
        """
        產生 5F40 查詢封包
        """
        self.seq = (self.seq + 1) & 0xFF
        seq = self.seq
        addr = int(tc_id)
        info = struct.pack('>BB', 0x5F, 0x40)
        escaped_info = self.escape_dle(info)
        commandLength = 10 + len(escaped_info)
        header = struct.pack('>BBBHH', 0xAA, 0xBB, seq, addr, commandLength)
        footer = struct.pack('>BB', 0xAA, 0xCC)
        cks = 0
        for b in header + info + footer:
            cks ^= b
        return header + info + footer + bytes([cks])

    def create_5f48_packet(self, tc_id):
        """
        產生 5F48 查詢封包
        """
        self.seq = (self.seq + 1) & 0xFF
        seq = self.seq
        addr = int(tc_id)
        info = struct.pack('>BB', 0x5F, 0x48)
        escaped_info = self.escape_dle(info)
        commandLength = 10 + len(escaped_info)
        header = struct.pack('>BBBHH', 0xAA, 0xBB, seq, addr, commandLength)
        footer = struct.pack('>BB', 0xAA, 0xCC)
        cks = 0
        for b in header + info + footer:
            cks ^= b
        return header + info + footer + bytes([cks])

    def create_5f18_packet(self, tc_id, plan_id):
        """
        產生 5F18 選擇執行之時制計畫封包
        """
        self.seq = (self.seq + 1) & 0xFF
        seq = self.seq
        addr = int(tc_id)
        info = struct.pack('>BBB', 0x5F, 0x18, plan_id)
        escaped_info = self.escape_dle(info)
        commandLength = 10 + len(escaped_info)
        header = struct.pack('>BBBHH', 0xAA, 0xBB, seq, addr, commandLength)
        footer = struct.pack('>BB', 0xAA, 0xCC)
        cks = 0
        for b in header + info + footer:
            cks ^= b
        return header + info + footer + bytes([cks])

    def create_0f10_packet(self, tc_id):
        """
        產生 0F10 重設定現場設備
        """
        self.seq = (self.seq + 1) & 0xFF
        seq = self.seq
        addr = int(tc_id)
        info = struct.pack('>BBBB', 0x0F, 0x10, 0x52, 0x52)
        escaped_info = self.escape_dle(info)
        commandLength = 10 + len(escaped_info)
        header = struct.pack('>BBBHH', 0xAA, 0xBB, seq, addr, commandLength)
        footer = struct.pack('>BB', 0xAA, 0xCC)
        cks  = 0
        for b in header + info + footer:
            cks ^= b
        return header + info + footer + bytes([cks])

    def create_5f3f_packet(self, tc_id, transmit_type, transmit_cycle):
        """
        產生 5F3F 設定傳送類型和傳送週期封包
        """
        self.seq = (self.seq + 1) & 0xFF
        seq = self.seq
        addr = int(tc_id)
        info = struct.pack('>BBBB', 0x5F, 0x3F, transmit_type, transmit_cycle)
        escaped_info = self.escape_dle(info)
        commandLength = 10 + len(escaped_info)
        header = struct.pack('>BBBHH', 0xAA, 0xBB, seq, addr, commandLength)
        footer = struct.pack('>BB', 0xAA, 0xCC)
        cks = 0
        for b in header + info + footer:
            cks ^= b
        return header + info + footer + bytes([cks])


    def set_tc_id(self, tc_id):
        """
        設定交通控制器ID
        """
        self.tc_id = tc_id

    def set_5f0c_callback(self, callback):
        """
        設定 5F0C 回報處理後的回調函式
        """
        self.f5f0c_callback = callback

