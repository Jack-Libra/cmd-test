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
from packet.center import PacketCenter
from packet.packet_definition import PacketDefinition
from utils import binary_list_to_int
from config.log_setup import setup_logging 
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
        self.center = PacketCenter(
            mode=mode,
            network=self.network,
            config=self.config,
            tc_id=self.tc_id,
            logger=self.logger
        )
        
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
                        packet = self.center.parse(frame)
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
        #self.center.process(packet)
        self.center.process_and_ack(packet, self.network, addr, self.logger)
        
    
class Command(Base):
    """指令下傳介面類：接收+命令雙線程，使用 seq 追蹤命令狀態"""
    
    def __init__(self, device_id=3, mode="command"):
        
        super().__init__(device_id, mode)

        self.packet_def = PacketDefinition()

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

        self.center.process_and_ack(packet, self.network, addr, self.logger)

    def _handle_command_response(self, packet, addr):
        """處理指令回應"""
        seq = packet.get("序列號")
        
        with self.pending_lock:
            if seq not in self.pending_commands:
                return
            
            cmd_info = self.pending_commands[seq]
            command = packet.get("指令編號")
            
            if command == "0F80":
                cmd_info['status'] = 'success'
                cmd_info['response_time'] = datetime.datetime.now().isoformat()
                self.logger.info(f"✓ 指令執行成功: {cmd_info['description']}")
            elif command == "0F81":
                error_code = packet.get("錯誤碼", 0)
                cmd_info['status'] = 'failed'
                cmd_info['error_code'] = error_code
                cmd_info['response_time'] = datetime.datetime.now().isoformat()
                self.logger.error(f"✗ 指令執行失敗: {cmd_info['description']} (錯誤碼: 0x{error_code:02X})")
            
            self.command_history.append(cmd_info)
            del self.pending_commands[seq]


# =============命令迴圈=============    

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

    def _execute_command(self, command_input: str):
        """執行指令"""
        try:
            parts = command_input.split()
            if not parts:
                return
            
            cmd_type = parts[0].upper()
            definition = self.packet_def.get_definition(cmd_type)
            
            if not definition:
                print(f"不支援的指令類型: {cmd_type}")
                return
            
            if definition.get("reply_type") not in ["查詢", "設定"]:
                print(f"{cmd_type} 不是可執行命令")
                return
            
            if definition.get("interaction_type") == "multi_step":
                print(f"{cmd_type} 指令需要多步驟輸入，目前尚未實現")
                return
            
            fields = definition.get("fields", [])

            # 檢查列表參數
            if any(f.get("type") == "list" for f in fields):
                print(f"{cmd_type} 指令包含列表參數，目前不支援")
                return
            
            # 檢查參數數量
            if len(parts[1:]) < len(fields):
                format_str = definition.get("format", cmd_type)
                example_str = definition.get("example", cmd_type)
                print(f"{cmd_type} 指令參數不足\n格式: {format_str}\n範例: {example_str}")
                return
            
            # 解析參數
            fields_dict = {}
            description_parts = [definition.get("description", cmd_type)]
            
            for i, field in enumerate(fields):
                field_name = field.get("name", f"參數{i}")
                input_type = field.get("input_type", "dec")  # fields 中已有 input_type
                
                try:
                    value = self._parse_param(parts[1:][i], field_name, input_type)
                except ValueError as e:
                    print(str(e))
                    return
                
                # 檢查範圍
                param_range = (0, 0xFF) 
                if not (param_range[0] <= value <= param_range[1]):
                    print(f"{field_name} 超出範圍 (0x{param_range[0]:02X}~0x{param_range[1]:02X}): {value}")
                    return
                
                fields_dict[field_name] = value
                description_parts.append(f"{field_name}:0x{value:02X}")
            
            # 發送命令並註冊
            description = " ".join(description_parts)
            seq = self._send_command(cmd_type, fields_dict, description)
            if seq:
                self._register_command(cmd_type, seq, definition)
        
        except Exception as e:
            print(f"指令執行錯誤: {e}")

    def _parse_param(self, value_str, param_name, input_type="dec"):
        """解析參數"""
        
        # 二進制
        if input_type == "binary":
            value_str = value_str.strip()
            if not all(c in '01' for c in value_str) or len(value_str) != 8:
                raise ValueError(f"{param_name} 二進制格式錯誤: 需要8位二進制字符串，如 10101010")
            bits = [int(bit) for bit in value_str]
            return binary_list_to_int(bits)
        
        # 十六進制
        elif input_type == "hex":
            if value_str.startswith('0x') or value_str.startswith('0X'):
                value_str = value_str[2:]
            if not all(c in '0123456789ABCDEFabcdef' for c in value_str):
                raise ValueError(f"{param_name} 格式錯誤: {value_str} (應為十六進制)")
            return int(value_str, 16)
        
        # 十進制
        else:
            if not value_str.isdigit():
                raise ValueError(f"{param_name} 格式錯誤: {value_str} (應為十進制數字)")
            return int(value_str, 10)
       
    def _send_command(self, cmd_code, fields, description):
        """發送指令封包"""
        try:
            seq = self.center.next_seq()
            frame = self.center.build(cmd_code, fields, seq=seq, addr=self.tc_id)
            
            if not frame:
                print(f"構建封包失敗: {cmd_code}")
                return None
            
            addr = (self.config.get_tc_ip(), self.config.get_tc_port())
            if self.network.send_data(frame, addr):
                self.logger.info(f"發送指令: {description} (SEQ: {seq})")
                self.logger.info(f"封包內容: {binascii.hexlify(frame).decode('ascii')}")
                return seq
            else:
                print("封包發送失敗")
                return None
                
        except Exception as e:
            self.logger.error(f"發送指令封包失敗: {e}", exc_info=True)
            print(f"發送失敗: {e}")
            return None

    def _register_command(self, cmd_code, seq, definition):
        """註冊命令到待處理列表"""
        cmd_info = {
            '序列號': seq,
            '號誌控制器ID': self.tc_id,
            '指令': cmd_code,
            'description': definition.get('description', cmd_code),
            'send_time': datetime.datetime.now().isoformat(),
            'status': 'pending'
        }
        with self.pending_lock:
            self.pending_commands[seq] = cmd_info
        print(f"指令已發送 (SEQ: {seq})")

# =============顯示說明=============    

    def _show_help(self):
        """顯示說明"""
        print(f"交通控制系統指令下傳介面 - TC{self.tc_id:03d}")
        print(f"可用指令: help, status, history, quit")
        
        # 動態獲取可執行命令
        executable_commands = {}
        for cmd_code, definition in self.packet_def.definitions.items():
            if definition.get("reply_type") in ["查詢", "設定"]:
                executable_commands[cmd_code] = definition
        
        if executable_commands:
            print(f"\n封包指令:")
            for cmd_code, definition in sorted(executable_commands.items()):
                format_str = definition.get("format", cmd_code)
                desc = definition.get("description", cmd_code)
                print(f"  {format_str:<45} - {desc}")
            
            print(f"\n範例:")
            for cmd_code, definition in sorted(executable_commands.items()):
                example = definition.get("example", cmd_code)
                print(f"  {example}")
        
    def _show_status(self):
        """顯示系統狀態"""
        with self.pending_lock:
            pending_count = len(self.pending_commands)
        
        print(f"\n系統狀態:")
        print(f"  控制器ID: TC{self.tc_id:03d}")
        print(f"  待處理指令: {pending_count}")
        print(f"  指令歷史: {len(self.command_history)}")
        
        if pending_count > 0:
            print("\n待處理指令:")
            with self.pending_lock:
                for seq, cmd_info in self.pending_commands.items():
                    print(f"  SEQ {seq}: {cmd_info['description']} ({cmd_info['send_time']})")
    
    def _show_history(self):
        """顯示指令歷史"""
        if not self.command_history:
            print("\n無指令歷史記錄")
            return
        
        print(f"\n指令歷史 (最近 {min(10, len(self.command_history))} 筆):")
        for cmd_info in self.command_history[-10:]:
            icon = "✓" if cmd_info['status'] == 'success' else "✗"
            print(f"  {icon} {cmd_info['description']}")
            print(f"    發送: {cmd_info['send_time']}")
            print(f"    回應: {cmd_info.get('response_time', '未回應')}")
            if cmd_info['status'] == 'failed':
                print(f"    錯誤: 0x{cmd_info.get('error_code', 0):02X}")






