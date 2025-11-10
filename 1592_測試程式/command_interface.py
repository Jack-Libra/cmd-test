"""
交通控制系統指令下傳介面
完全移除所有會干擾終端輸入的日誌輸出
"""
import threading
import time
import os
import logging
import datetime
from utils.tc_core import *
from utils.log_setup import *
from utils.tc_config import TCConfig
from utils.tc_network import TCNetwork
from utils.tc_protocol import TrafficControlProtocol

class CommandInterfaceQuiet:
    """指令下傳介面類"""
    
    def __init__(self, device_id=3):
        self.device_id = device_id
        self.config = TCConfig(device_id)
        self.network = None
        self.protocol = None
        self.tc_id = None
        self.running = False
        
        # 指令追蹤
        self.pending_commands = {}  # {seq: command_info}
        self.command_history = []   # 指令歷史記錄
        
        # 執行緒控制
        self.receive_thread = None
        self.command_thread = None
        
        # 日誌
        self._setup_silent_logging()
        
        self._init_system()
    
    def _setup_silent_logging(self):
        """日誌系統 - 修正重複記錄問題"""
        # 取得現有的日誌器
        logger = logging.getLogger("tc")
        
        # 清除所有處理器
        logger.handlers.clear()
        
        # 只添加檔案處理器，完全不輸出到終端
        LOG_DIR = "logs"
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
        LOG_FILE = os.path.join(LOG_DIR, 'traffic_control.log')
        
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
        
        # 設定根日誌器也靜音，但避免重複處理器
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        # 不重複添加處理器到根日誌器，避免重複記錄
        root_logger.setLevel(logging.WARNING)
    
    def _init_system(self):
        """初始化系統"""
        # 設定TC ID
        tc_id_str = self.config.get_tc_id()
        if isinstance(tc_id_str, str) and tc_id_str.startswith('TC'):
            self.tc_id = int(tc_id_str.replace('TC', ''))
        else:
            self.tc_id = int(tc_id_str)
        
        # 初始化網路
        self.network = TCNetwork(
            local_ip=self.config.get_transserver_ip(),
            local_port=self.config.get_transserver_port(),
            server_ip=self.config.get_tc_ip(),
            server_port=self.config.get_tc_port()
        )
        
        # 初始化協議
        self.protocol = TrafficControlProtocol(network=self.network)
        self.protocol.set_tc_id(self.tc_id)
        
        print(f"指令介面初始化完成 - TC{self.tc_id:03d}")
    
    def start(self):
        """啟動系統"""
        if not self.network.open():
            print("開啟 UDP 連接失敗")
            return False
        
        self.running = True
        
        # 啟動封包接收執行緒
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        
        # 啟動指令介面執行緒
        self.command_thread = threading.Thread(target=self._command_loop, daemon=True)
        self.command_thread.start()
        
        print("指令下傳系統已啟動")
        print("注意：所有日誌只記錄到 logs/traffic_control.log")
        return True
    
    def stop(self):
        """停止系統"""
        self.running = False
        if self.network:
            self.network.close()
        print("指令下傳系統已停止")
    
    def _receive_loop(self):
        """封包接收迴圈"""
        while self.running:
            try:
                data, addr = self.network.receive_data()
                if addr and data:
                    packets = self.network.process_buffer(data)
                    for packet in packets:
                        self._handle_received_packet(packet)
                time.sleep(0.01)
            except Exception as e:
                log_error(f"封包接收錯誤: {e}")
                time.sleep(0.1)
    
    def _handle_received_packet(self, packet):
        """處理接收到的封包"""
        if not packet:
            return
        
        command = packet.get("command", "")
        seq = packet.get("seq", 0)
        
        # 檢查是否為指令回應
        if command in ["0F80", "0F81"]:
            self._handle_command_response(packet)
        
        # 處理其他封包 (只記錄到檔案)
        self.network.process_packet(packet)
    
    def _handle_command_response(self, packet):
        """處理指令回應"""
        command = packet.get("command", "")
        seq = packet.get("seq", 0)
        tc_id = packet.get("tc_id", 0)
        
        if seq in self.pending_commands:
            cmd_info = self.pending_commands[seq]
            
            if command == "0F80":
                log_info(f"✓ 指令執行成功: {cmd_info['description']}")
                print(f"✓ 指令執行成功: {cmd_info['description']}")
                cmd_info['status'] = 'success'
                cmd_info['response_time'] = datetime.datetime.now().isoformat()
            elif command == "0F81":
                error_code = packet.get("error_code", 0)
                log_error(f"✗ 指令執行失敗: {cmd_info['description']} (錯誤碼: 0x{error_code:02X})")
                print(f"✗ 指令執行失敗: {cmd_info['description']} (錯誤碼: 0x{error_code:02X})")
                cmd_info['status'] = 'failed'
                cmd_info['error_code'] = error_code
                cmd_info['response_time'] = datetime.datetime.now().isoformat()
            
            
            # 移到歷史記錄
            self.command_history.append(cmd_info)
            del self.pending_commands[seq]
    
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
                elif command_input.lower() == 'clear':
                    self._clear_screen()
                elif command_input.lower() == 'log':
                    self._show_recent_logs()
                else:
                    self._execute_command(command_input)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"指令處理錯誤: {e}")
        
        self.running = False
    
    def _clear_screen(self):
        """清除螢幕"""
        os.system('cls' if os.name == 'nt' else 'clear')
        self._show_help()
    
    def _show_recent_logs(self):
        """顯示最近的日誌"""
        try:
            log_file = "logs/traffic_control.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    recent_lines = lines[-20:] if len(lines) > 20 else lines
                    print("\n最近的日誌記錄:")
                    print("-" * 60)
                    for line in recent_lines:
                        print(line.strip())
                    print("-" * 60)
            else:
                print("日誌檔案不存在")
        except Exception as e:
            print(f"讀取日誌失敗: {e}")
    
    def _show_help(self):
        """顯示說明"""
        print("\n" + "="*60)
        print("交通控制系統指令下傳介面")
        print("="*60)
        print("可用指令:")
        print("  help     - 顯示此說明")
        print("  status   - 顯示系統狀態")
        print("  history  - 顯示指令歷史")
        print("  clear    - 清除螢幕")
        print("  log      - 顯示最近日誌")
        print("  quit     - 退出程式")
        print("\n指令下傳格式:")
        print("  5F16 <segmentType> <segmentCount> <time1> <planId1> [<time2> <planId2> ...] <weekDays>")
        print("  5F46 <segmentType> <weekDays>")
        print("  5F10 <controlStrategy> <effectTime>")
        print("  0F40 <equipmentNo>")
        print("  5F3F <transmitType> <transmitCycle>")
        print("  5F40")
        print("  5F48")
        print("  5F18 <planId>")
        print("\n範例:")
        print("  5F16 1 2 08:00 1 18:00 2 1,2,3,4,5")
        print("  5F46 1 1,2,3,4,5")
        print("  5F10 1 60")
        print("  5F3F 1 1")
        print("  5F18 1")
        print("  0F40 0")
        print("  5F40")
        print("  5F48")
        print("  0F10")
        print("="*60)
    
    def _show_status(self):
        """顯示系統狀態"""
        print(f"\n系統狀態:")
        print(f"  控制器ID: TC{self.tc_id:03d}")
        print(f"  控制器地址: {self.config.get_tc_ip()}:{self.config.get_tc_port()}")
        print(f"  本地地址: {self.config.get_transserver_ip()}:{self.config.get_transserver_port()}")
        print(f"  待處理指令: {len(self.pending_commands)}")
        print(f"  指令歷史: {len(self.command_history)}")
        
        if self.pending_commands:
            print("\n待處理指令:")
            for seq, cmd_info in self.pending_commands.items():
                print(f"  SEQ {seq}: {cmd_info['description']} (發送時間: {cmd_info['send_time']})")
    
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
    
    def _execute_command(self, command_input):
        """執行指令"""
        try:
            parts = command_input.split()
            cmd_type = parts[0].upper()
            
            if cmd_type == "5F16":
                self._execute_5f16_command(parts[1:])
            elif cmd_type == "5F46":
                self._execute_5f46_command(parts[1:])
            elif cmd_type == "0F40":
                self._execute_0f40_command(parts[1:])
            elif cmd_type == "5F10":
                self._execute_5f10_command(parts[1:])
            elif cmd_type == "5F40":
                self._execute_5f40_command(parts[1:])
            elif cmd_type == "5F48":
                self._execute_5f48_command(parts[1:])
            elif cmd_type == "5F18":
                self._execute_5f18_command(parts[1:])
            elif cmd_type == "0F10":
                self._execute_0f10_command(parts[1:])
            elif cmd_type == "5F3F":
                self._execute_5f3f_command(parts[1:])
            else:
                print(f"不支援的指令類型: {cmd_type}")
                
        except Exception as e:
            print(f"指令執行錯誤: {e}")
    
    def _execute_5f16_command(self, args):
        """執行 5F16 指令"""
        if len(args) < 4:
            print("5F16 指令參數不足")
            return
        
        try:
            segment_type = int(args[0])
            segment_count = int(args[1])
            
            # 解析時段資訊
            segments = []
            for i in range(segment_count):
                time_idx = 2 + i * 2
                plan_idx = 3 + i * 2
                if time_idx >= len(args) or plan_idx >= len(args):
                    print("時段參數不足")
                    return
                
                segments.append({
                    'time': args[time_idx],
                    'planId': int(args[plan_idx])
                })
            
            # 解析星期參數
            weekdays_str = args[-1]
            weekdays = [int(x.strip()) for x in weekdays_str.split(',')]
            
            # 建立封包
            segment_info = {
                'segmentType': segment_type,
                'segmentCount': segment_count,
                'beginTime': segments,
                'numWeekDay': len(weekdays),
                'weekDay': weekdays
            }
            
            packet = self.protocol.create_5f16_packet(self.tc_id, segment_info)
            if packet:
                self._send_command_packet(packet, "5F16", f"設定時段型態 (類型:{segment_type}, 時段數:{segment_count})")
            else:
                print("建立 5F16 封包失敗")
                
        except Exception as e:
            print(f"5F16 指令參數錯誤: {e}")
    
    def _execute_5f46_command(self, args):
        """執行 5F46 指令"""
        if len(args) < 2:
            print("5F46 指令參數不足")
            return
        
        try:
            segment_type = int(args[0])
            weekdays_str = args[1]
            weekdays = [int(x.strip()) for x in weekdays_str.split(',')]
            
            # 建立封包
            segment_info = {
                'segmentType': segment_type,
                'weekDay': weekdays
            }
            
            packet = self.protocol.create_5f46_packet(self.tc_id, segment_info)
            if packet:
                self._send_command_packet(packet, "5F46", f"查詢時段型態 (類型:{segment_type})")
            else:
                print("建立 5F46 封包失敗")
                
        except Exception as e:
            print(f"5F46 指令參數錯誤: {e}")
    
    def _execute_0f40_command(self, args):
        """執行 0F40 指令"""
        if len(args) < 1:
            print("0F40 指令參數不足")
            return
        
        try:
            equipment_no = int(args[0])
            packet = self.protocol.create_0f40_packet(self.tc_id, equipment_no)
            if packet:
                self._send_command_packet(packet, "0F40", f"查詢現場設備編號 (編號:{equipment_no})")
            else:
                print("建立 0F40 封包失敗")
    
        except Exception as e:
            print(f"0F40 指令參數錯誤: {e}")
    
    def _execute_5f10_command(self, args):
        """執行 5F10 指令 - 設定控制策略
        
        控制策略位元組合說明：
        Bit 0 (0x01) = 1  : 定時控制
        Bit 1 (0x02) = 2  : 動態控制  
        Bit 2 (0x04) = 4  : 路口手動
        Bit 3 (0x08) = 8  : 中央手動
        Bit 4 (0x10) = 16 : 時相控制
        Bit 5 (0x20) = 32 : 即時控制
        Bit 6 (0x40) = 64 : 觸動控制
        Bit 7 (0x80) = 128: 特別路線控制
        
        組合模式範例：
        - 定時控制 + 動態控制 = 1 + 2 = 3
        - 時相控制 + 即時控制 = 16 + 32 = 48
        - 定時控制 + 時相控制 + 即時控制 = 1 + 16 + 32 = 49
        """
        if len(args) < 2:
            print("5F10 指令參數不足")
            print("格式: 5F10 <controlStrategy> <effectTime>")
            print("範例: 5F10 1 60")
            return
    
        try:
            control_strategy = int(args[0])
            effect_time = int(args[1])
            
            # 參數驗證
            if not (0 <= control_strategy <= 255):
                print("錯誤: controlStrategy 必須是 0-255 之間的整數")
                return
            if not (0 <= effect_time <= 255):
                print("錯誤: effectTime 必須是 0-255 之間的整數")
                return
            
            # 建立封包
            packet = self.protocol.create_5f10_packet(self.tc_id, control_strategy, effect_time)
            if packet:
                # 解析控制策略位元說明
                strategy_desc = self._get_control_strategy_description(control_strategy)
                self._send_command_packet(packet, "5F10", f"設定控制策略 (策略:{control_strategy:02X}, 有效時間:{effect_time}分鐘) - {strategy_desc}")
            else:
                print("建立 5F10 封包失敗")
    
        except ValueError:
            print("錯誤: controlStrategy 和 effectTime 必須是有效的整數")
        except Exception as e:
            print(f"5F10 指令參數錯誤: {e}")

    def _execute_5f40_command(self, args):
        """執行 5F40 指令"""
        if len(args) < 0:
            print("5F40 指令參數不足")
            return
        try:
            packet = self.protocol.create_5f40_packet(self.tc_id)
            if packet:
                self._send_command_packet(packet, "5F40", "查詢控制策略")
            else:
                print("建立 5F40 封包失敗")
    
        except Exception as e:
            print(f"5F40 指令參數錯誤: {e}")

    def _execute_5f18_command(self, args):
        """執行 5F18 指令"""
        if len(args) < 1:
            print("5F18 指令參數不足")
            return
        try:
            plan_id = int(args[0])
            packet = self.protocol.create_5f18_packet(self.tc_id, plan_id)
            if packet:
                self._send_command_packet(packet, "5F18", "選擇執行之時制計畫")
            else:
                print("建立 5F18 封包失敗")
    
        except Exception as e:
            print(f"5F18 指令參數錯誤: {e}")

    def _execute_5f48_command(self, args):
        """執行 5F48 指令"""
        if len(args) < 0:
            print("5F48 指令參數不足")
            return
        try:
            packet = self.protocol.create_5f48_packet(self.tc_id)
            if packet:
                self._send_command_packet(packet, "5F48", "查詢目前時制計畫內容")
            else:
                print("建立 5F48 封包失敗")
    
        except Exception as e:
            print(f"5F48 指令參數錯誤: {e}")

    def _execute_0f10_command(self, args):
        """執行 0F10 指令"""
        try:
            packet = self.protocol.create_0f10_packet(self.tc_id)
            if packet:
                self._send_command_packet(packet, "0F10", "重設定現場設備")
            else:
                print("建立 0F10 封包失敗")

        except Exception as e:
            print(f"0F10 指令參數錯誤: {e}")

    def _execute_5f3f_command(self, args):
        """執行 5F3F 指令"""
        if len(args) < 2:
            print("5F3F 指令參數不足")
            return
        try:
            transmit_type = int(args[0])
            transmit_cycle = int(args[1])
            packet = self.protocol.create_5f3f_packet(self.tc_id, transmit_type, transmit_cycle)
            if packet:
                self._send_command_packet(packet, "5F3F", "設定傳送類型和傳送週期")
            else:
                print("建立 5F3F 封包失敗")
        except Exception as e:
            print(f"5F3F 指令參數錯誤: {e}")


    def _get_control_strategy_description(self, control_strategy):
        """取得控制策略描述"""
        strategies = []
        if control_strategy & 0x01:
            strategies.append("定時控制")
        if control_strategy & 0x02:
            strategies.append("動態控制")
        if control_strategy & 0x04:
            strategies.append("路口手動")
        if control_strategy & 0x08:
            strategies.append("中央手動")
        if control_strategy & 0x10:
            strategies.append("時相控制")
        if control_strategy & 0x20:
            strategies.append("即時控制")
        if control_strategy & 0x40:
            strategies.append("觸動控制")
        if control_strategy & 0x80:
            strategies.append("特別路線控制")
        
        return "、".join(strategies) if strategies else "無設定策略"
    
    def _send_command_packet(self, packet, command_type, description):
        """發送指令封包"""
        try:
            # 取得序列號
            seq = self.protocol.next_seq()
            
            # 記錄指令
            cmd_info = {
                'seq': seq,
                'command_type': command_type,
                'description': description,
                'send_time': datetime.datetime.now().isoformat(),
                'status': 'pending'
            }
            self.pending_commands[seq] = cmd_info
            
            # 發送封包
            if self.network.send_packet(packet):
                # 只記錄到檔案，不重複記錄
                log_info(f"發送指令: {description} (SEQ: {seq})")
                print(f"✓ 指令已發送: {description}")
            else:
                print("✗ 封包發送失敗")
                del self.pending_commands[seq]
                
        except Exception as e:
            log_error(f"發送指令封包失敗: {e}")
            print(f"✗ 發送失敗: {e}")

def main():
    """主程式"""
    interface = CommandInterfaceQuiet(device_id=3)
    
    if not interface.start():
        return
    
    try:
        interface.command_thread.join()
    except KeyboardInterrupt:
        print("程式被中斷")
    finally:
        interface.stop()

if __name__ == "__main__":
    main()
