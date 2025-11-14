# command.py

"""
交通控制系統指令下傳介面
基類架構：Base -> Command, Receive
"""

import threading
import time
import datetime
from config.config import TCConfig
from config.network import UDPTransport
from packet.registry import PacketCenter
from config.log_setup import setup_logging 
from config.commands import COMMAND_METADATA, COMMAND_HANDLERS, COMMANDS_BY_CATEGORY
import binascii


class Base:
    """基類：提供共同的初始化和接收功能"""

    def __init__(self, device_id=3, mode: str = "receive"):
        self.mode = mode
        self.device_id = device_id
        
        
        # 設置日誌文件名
        log_file_map = {
            "receive": "receive.log",
            "command": "command.log",
        }
        log_file = log_file_map.get(mode, "receive.log")
        
        # 初始化日誌
        self.logger = setup_logging(log_file=log_file, mode=mode)
        
        self.config = TCConfig(device_id)
        
        self.tc_id = device_id
        
        # 初始化網路
        self.network = UDPTransport(
            local_ip=self.config.get_transserver_ip(),
            local_port=self.config.get_transserver_port(),
            server_ip=self.config.get_tc_ip(),
            server_port=self.config.get_tc_port()
        )
        
        # 初始化封包註冊中心
        self.registry = PacketCenter(mode=mode)
        
        # 執行緒控制
        self.running = False
        self.receive_thread = None
        
        self.logger.info(f"系統初始化完成 - {mode}模式")


    def start(self):
        """啟動系統（子類可覆寫）"""
        if not self.network.open():
            self.logger.error("開啟 UDP 連接失敗")
            return False
        
        self.running = True
        return True
    
    def stop(self):
        """停止系統"""
        self.running = False
        if self.network:
            self.network.close()
        self.logger.info("系統已停止")
    
    def _receive_loop(self):
        """封包接收迴圈（子類可覆寫）"""
        self.logger.info("接收線程已啟動")
        
        while self.running:
            try:
                data, addr = self.network.receive_data()
                if addr and data:
                    # 處理緩衝區，獲取完整幀列表
                    frames = self.network.process_buffer(data)
                    
                    for frame in frames:
                        # 檢查是否為原始ACK封包
                        if len(frame) >= 3 and frame[0] == 0xAA and frame[1] == 0xDD:
                            frame_hex = binascii.hexlify(frame).decode('ascii').upper()
                            self.logger.info(f"收到原始ACK封包: {frame_hex} 來自 {addr[0]}:{addr[1]}")                        
                        
                        
                        # 解析封包
                        packet = self.registry.parse(frame)
                        if packet:
                            # 處理接收到的封包（子類實現）
                            self._handle_received_packet(packet, addr)
                
                time.sleep(0.01)
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"封包接收錯誤: {e}", exc_info=True)
                time.sleep(0.1)
        
        self.logger.info("接收線程已停止")
    
    def _handle_received_packet(self, packet, addr):
        """處理接收到的封包（子類實現）"""
        pass

class Receive(Base):
    """接收模式：只接收數據，不發送命令"""
    def __init__(self, device_id=3, mode: str = "receive"):
        super().__init__(device_id, mode)

    def start(self):
        """啟動接收模式"""
        if not super().start():
            return False
        
        # 啟動封包接收執行緒
        self.receive_thread = threading.Thread(
            target=self._receive_loop,
            name="ReceiveThread",
            daemon=True
        )
        self.receive_thread.start()
        
        try:
            self.logger.info("接收模式已啟動")
            self.receive_thread.join()
        
        except KeyboardInterrupt:
            self.logger.info("\n接收模式已停止")
        
        finally:
            self.stop()
        
        return True
    
    def _handle_received_packet(self, packet, addr):
        """處理接收到的封包（覆寫基類方法，不發送ACK）"""
        if not packet:
            return
        
        # 處理封包(並發送ACK)
        #self.registry.process(packet)
        self.registry.process_and_ack(packet, self.network, addr, self.logger)
        
    
class Command(Base):
    """指令下傳介面類：接收+命令雙線程，使用 seq 追蹤命令狀態"""
    
    COMMAND_HANDLERS = COMMAND_HANDLERS  # 從 config.commands 導入
    
    def __init__(self, device_id=3, mode="command"):
        super().__init__(device_id, mode)
        
        # 指令追蹤
        self.pending_commands = {}  # {seq: command_info}
        self.command_history = []   # 指令歷史記錄
        self.pending_lock = threading.Lock()  # 保護 pending_commands
        
        # 命令線程
        self.command_thread = None
        
        self.logger.info(f"指令介面初始化完成 - TC{self.tc_id:03d}")
    
    def start(self):
        """啟動系統"""
        if not super().start():
            return False
        
        # 啟動封包接收執行緒
        self.receive_thread = threading.Thread(
            target=self._receive_loop,
            name="ReceiveThread",
            daemon=True
        )
        self.receive_thread.start()
        
        # 啟動指令介面執行緒
        self.command_thread = threading.Thread(
            target=self._command_loop,
            name="CommandThread",
            daemon=True
        )
        self.command_thread.start()
        try:
            self.logger.info("命令模式已啟動")
            self.command_thread.join()
        except KeyboardInterrupt:
            self.logger.info("\n命令模式已停止")
        finally:
            self.stop()
        
        return True
    
    def _handle_received_packet(self, packet, addr):
        """處理接收到的封包（覆寫基類方法）"""
        
        command = packet.get("指令編號")
        
        # 檢查是否為指令回應（0F80/0F81/5F80/5F81）
        if command in ["0F80", "0F81"]:
            self.logger.info(f"處理 {command} 封包: {packet}")
            self._handle_command_response(packet, addr)
            self.registry.process_and_ack(packet, self.network, addr, self.logger)
        else:
            # 處理封包並發送ACK
            self.registry.process_and_ack(packet, self.network, addr, self.logger)
    
    def _handle_command_response(self, packet, addr):
        """處理指令回應"""
        command = packet.get("指令編號")
        seq = packet.get("序列號")
        
        with self.pending_lock:
            if seq not in self.pending_commands:
                return
            
            cmd_info = self.pending_commands[seq]
            
            # 判斷成功或失敗
            is_success = command in ["設定/查詢回報（成功）", "0F80", "5F80"]
            is_failure = command in ["設定/查詢回報（失敗）", "0F81", "5F81"]
            
            if is_success:
                self._update_command_status(cmd_info, 'success')
                self.logger.info(f"✓ 指令執行成功: {cmd_info['description']}")
            elif is_failure:
                error_code = packet.get("錯誤碼", 0)
                self._update_command_status(cmd_info, 'failed', error_code)
                self.logger.error(
                    f"✗ 指令執行失敗: {cmd_info['description']} "
                    f"(錯誤碼: 0x{error_code:02X})"
                )
            
            # 移到歷史記錄
            self.command_history.append(cmd_info)
            del self.pending_commands[seq]
    
    def _update_command_status(self, cmd_info, status, error_code=0):
        """更新指令狀態"""
        cmd_info['status'] = status
        cmd_info['response_time'] = datetime.datetime.now().isoformat()
        if status == 'failed':
            cmd_info['error_code'] = error_code
    
    def _command_loop(self):
        """指令輸入迴圈"""
        self._show_help()
        
        while self.running:
            try:
                command_input = input("\n請輸入指令 (輸入 'help' 查看說明): ").strip()
                if not command_input:
                    continue
                
                if command_input.lower() == 'quit':
                    break
                elif command_input.lower() == 'help':
                    self._show_help()
                elif command_input.lower() == 'status':
                    self._show_status()
                elif command_input.lower() == 'history':
                    self._show_history()
                else:
                    self._execute_command(command_input)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.info(f"指令處理錯誤: {e}")
        
        self.running = False
    
    # ========== 工具方法 ==========
    
    def _parse_hex_or_int(self, value_str, param_name="值"):
        """
        解析十六進制或十進制字符串
        
        Args:
            value_str: 輸入字符串
            param_name: 參數名稱（用於錯誤提示）
        
        Returns:
            (value, error_message) - 成功返回 (值, None)，失敗返回 (None, 錯誤信息)
        """
        try:
            if value_str.startswith('0x') or value_str.startswith('0X'):
                return int(value_str, 16), None
            elif all(c in '0123456789ABCDEFabcdef' for c in value_str):
                return int(value_str, 16), None
            else:
                return int(value_str), None
        except ValueError:
            return None, f"{param_name} 格式錯誤: {value_str}"
    
    def _validate_range(self, value, min_val, max_val, param_name="值"):
        """驗證值是否在範圍內"""
        if not (min_val <= value <= max_val):
            return False, f"{param_name} 超出範圍 (0x{min_val:02X}~0x{max_val:02X} 或 {min_val}~{max_val}): {value}"
        return True, None
    
    def _show_help(self):
        """顯示說明（自動從元數據生成）"""
        print(f"交通控制系統指令下傳介面 - TC{self.tc_id:03d}")
        print(f"可用指令:")
        print(f"  help     - 顯示此說明")
        print(f"  status   - 顯示系統狀態")
        print(f"  history  - 顯示指令歷史")
        print(f"  quit     - 退出程式")
        
        # 按類別顯示命令
        for category, commands in COMMANDS_BY_CATEGORY.items():
            if commands:
                print(f"\n{category}指令:")
                for cmd_code in sorted(commands):
                    meta = COMMAND_METADATA[cmd_code]
                    print(f"  {meta['format']:<45} - {meta['description']}")
        
        print(f"\n範例:")
        for cmd_code, meta in sorted(COMMAND_METADATA.items()):
            print(f"  {meta['example']}")
        
    def _show_status(self):
        """顯示系統狀態"""
        with self.pending_lock:
            pending_count = len(self.pending_commands)
        
        print(f"\n系統狀態:")
        print(f"  控制器ID: TC{self.tc_id:03d}")
        print(f"  控制器地址: {self.config.get_tc_ip()}:{self.config.get_tc_port()}")
        print(f"  本地地址: {self.config.get_transserver_ip()}:{self.config.get_transserver_port()}")
        print(f"  待處理指令: {pending_count}")
        print(f"  指令歷史: {len(self.command_history)}")
        
        if pending_count > 0:
            print("\n待處理指令:")
            with self.pending_lock:
                for seq, cmd_info in self.pending_commands.items():
                    print(f"  SEQ {seq}: {cmd_info['description']} "
                          f"(發送時間: {cmd_info['send_time']})")
    
    def _show_history(self):
        """顯示指令歷史"""
        if not self.command_history:
            print("\n無指令歷史記錄")
            return
        
        print(f"\n指令歷史 (最近 {min(10, len(self.command_history))} 筆):")
        for cmd_info in self.command_history[-10:]:
            status_icon = "✓" if cmd_info['status'] == 'success' else "✗"
            print(f"  {status_icon} {cmd_info['description']}")
            print(f"    發送: {cmd_info['send_time']}")
            print(f"    回應: {cmd_info.get('response_time', '未回應')}")
            if cmd_info['status'] == 'failed':
                print(f"    錯誤: 0x{cmd_info.get('error_code', 0):02X}")
    
    def _execute_command(self, command_input: str):
        """執行指令"""
        try:
            parts = command_input.split()
            if not parts:
                return
            
            cmd_type = parts[0].upper()
            handler_name = self.COMMAND_HANDLERS.get(cmd_type)
            
            if handler_name:
                handler = getattr(self, handler_name)
                handler(parts[1:])
            else:
                print(f"不支援的指令類型: {cmd_type}")
                print(f"可用指令: {', '.join(sorted(COMMAND_METADATA.keys()))}")
                print(f"輸入 'help' 查看詳細說明")
        
        except Exception as e:
            print(f"指令執行錯誤: {e}")   

    def _execute_5f40_command(self, args):
        """執行 5F40 指令（查詢控制策略）"""
        meta = COMMAND_METADATA["5F40"]
        try:
            self._send_command("5F40", {}, meta["description"], addr=self.tc_id)
        except Exception as e:
            print(f"5F40 指令錯誤: {e}")
    
    def _execute_5f10_command(self, args):
        """執行 5F10 指令（設定控制策略）"""
        meta = COMMAND_METADATA["5F10"]
        
        if len(args) < len(meta["params"]):
            print(f"5F10 指令參數不足")
            print(f"格式: {meta['format']}")
            print(f"範例: {meta['example']}")
            return
        
        try:
            control_strategy = int(args[0])
            effect_time = int(args[1])
            
            # 使用元數據定義驗證範圍
            param_defs = meta["params"]
            valid, error = self._validate_range(control_strategy, param_defs[0]["range"][0], param_defs[0]["range"][1], "控制策略")
            if not valid:
                print(error)
                return
            
            valid, error = self._validate_range(effect_time, param_defs[1]["range"][0], param_defs[1]["range"][1], "有效時間")
            if not valid:
                print(error)
                return
            
            fields = {
                "control_strategy": control_strategy,
                "effect_time": effect_time
            }
            
            self._send_command(
                "5F10",
                fields,
                f"{meta['description']} (策略:0x{control_strategy:02X}, 時間:{effect_time}分鐘)",
                addr=self.tc_id
            )
        except ValueError as e:
            print(f"5F10 指令參數錯誤: {e}")
        except Exception as e:
            print(f"5F10 指令錯誤: {e}")
    
    def _execute_5f48_command(self, args):
        """執行 5F48 指令（查詢時制計畫）"""
        meta = COMMAND_METADATA["5F48"]
        try:
            self._send_command("5F48", {}, meta["description"], addr=self.tc_id)
        except Exception as e:
            print(f"5F48 指令錯誤: {e}")
    
    def _execute_5f18_command(self, args):
        """執行 5F18 指令（選擇時制計畫）"""
        meta = COMMAND_METADATA["5F18"]
        
        if len(args) < len(meta["params"]):
            print(f"5F18 指令參數不足")
            print(f"格式: {meta['format']}")
            print(f"範例: {meta['example']}")
            return
        
        try:
            plan_id = int(args[0])
            
            # 使用元數據定義驗證範圍
            param_def = meta["params"][0]
            valid, error = self._validate_range(plan_id, param_def["range"][0], param_def["range"][1], "時制計畫編號")
            if not valid:
                print(error)
                return
            
            fields = {"plan_id": plan_id}
            self._send_command("5F18", fields, f"{meta['description']} (計畫ID:{plan_id})", addr=self.tc_id)
        except ValueError as e:
            print(f"5F18 指令參數錯誤: {e}")
        except Exception as e:
            print(f"5F18 指令錯誤: {e}")

    def _execute_5f43_command(self, args):
        """執行 5F43 指令（查詢時相排列）"""
        meta = COMMAND_METADATA["5F43"]
        
        if len(args) < len(meta["params"]):
            print(f"5F43 指令參數不足")
            print(f"格式: {meta['format']}")
            print(f"範例: {meta['example']}")
            return
        
        try:
            # 解析參數
            phase_order, error = self._parse_hex_or_int(args[0], "時相編號")
            if error:
                print(error)
                return
            
            # 驗證範圍
            param_def = meta["params"][0]
            valid, error = self._validate_range(phase_order, param_def["range"][0], param_def["range"][1], "時相編號")
            if not valid:
                print(error)
                return
            
            fields = {"phase_order": phase_order}
            
            self._send_command(
                "5F43",
                fields,
                f"{meta['description']} (時相編號:0x{phase_order:02X})",
                addr=self.tc_id
            )
        except Exception as e:
            print(f"5F43 指令錯誤: {e}")
    
    def _execute_5f13_command(self, args):
        """執行 5F13 指令（設定時相排列）"""
        meta = COMMAND_METADATA["5F13"]
        
        # 驗證基本參數數量（前4個固定參數）
        if len(args) < 4:
            print(f"5F13 指令參數不足")
            print(f"格式: {meta['format']}")
            print(f"範例: {meta['example']}")
            return
        
        try:
            # 解析前4個基本參數
            phase_order, error = self._parse_hex_or_int(args[0], "時相編號")
            if error:
                print(error)
                return
            
            signal_map, error = self._parse_hex_or_int(args[1], "號誌位置圖")
            if error:
                print(error)
                return
            
            signal_count = int(args[2])
            sub_phase_count = int(args[3])
            
            # 驗證參數範圍（使用元數據定義）
            param_defs = meta["params"]
            valid, error = self._validate_range(phase_order, param_defs[0]["range"][0], param_defs[0]["range"][1], "時相編號")
            if not valid:
                print(error)
                return
            
            valid, error = self._validate_range(signal_map, param_defs[1]["range"][0], param_defs[1]["range"][1], "號誌位置圖")
            if not valid:
                print(error)
                return
            
            valid, error = self._validate_range(signal_count, param_defs[2]["range"][0], param_defs[2]["range"][1], "信號燈數量")
            if not valid:
                print(error)
                return
            
            valid, error = self._validate_range(sub_phase_count, param_defs[3]["range"][0], param_defs[3]["range"][1], "綠燈分相數目")
            if not valid:
                print(error)
                return
            
            # 解析信號狀態列表
            expected_status_count = signal_count * sub_phase_count
            if len(args) < 4 + expected_status_count:
                print(f"信號狀態列表參數不足")
                print(f"需要 {expected_status_count} 個狀態值 (signalCount * subPhaseCount)")
                print(f"實際提供: {len(args) - 4} 個")
                return
            
            signal_status_list = []
            for i in range(4, 4 + expected_status_count):
                status, error = self._parse_hex_or_int(args[i], f"信號狀態[{i-4}]")
                if error:
                    print(error)
                    return
                
                valid, error = self._validate_range(status, 0, 0xFF, f"信號狀態[{i-4}]")
                if not valid:
                    print(error)
                    return
                
                signal_status_list.append(status)
            
            fields = {
                "phase_order": phase_order,
                "號誌位置圖": signal_map,
                "signal_count": signal_count,
                "sub_phase_count": sub_phase_count,
                "信號狀態列表": signal_status_list
            }
            
            self._send_command(
                "5F13",
                fields,
                f"{meta['description']} (時相:0x{phase_order:02X}, 方向:{signal_count}, 分相:{sub_phase_count})",
                addr=self.tc_id
            )
        except ValueError as e:
            print(f"5F13 指令參數錯誤: {e}")
            print("請檢查參數格式是否正確")
        except Exception as e:
            print(f"5F13 指令錯誤: {e}")
                
    def _send_command(self, cmd_code, fields, description, addr):
        """發送指令封包"""
        try:
            # 獲取序列號
            seq = self.registry.next_seq()
            
            # 構建封包
            frame = self.registry.build(cmd_code, fields, seq=seq, addr=self.tc_id)
            
            if not frame:
                print(f"構建封包失敗: {cmd_code}")
                return
            
            # 記錄指令（用於追蹤）
            cmd_info = {
                '序列號': seq,
                '號誌控制器ID': self.tc_id,
                '指令': cmd_code,
                'description': description,
                'send_time': datetime.datetime.now().isoformat(),
                'status': 'pending'
            }
            
            with self.pending_lock:
                self.pending_commands[seq] = cmd_info
            
            # 發送封包
            if self.network.send_data(frame, addr=(self.config.get_tc_ip(), self.config.get_tc_port())):
                self.logger.info(f"發送指令: {description} (SEQ: {seq})")
                
                self.logger.info(f"封包內容: {binascii.hexlify(frame).decode('ascii')}")
            else:
                self.logger.error("封包發送失敗")
                with self.pending_lock:
                    if seq in self.pending_commands:
                        del self.pending_commands[seq]
                
        except Exception as e:
            self.logger.error(f"發送指令封包失敗: {e}", exc_info=True)
            self.logger.error(f"發送失敗: {e}")