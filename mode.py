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

from config.log_setup import setup_logging 
import binascii

from command.session_manager import SessionManager
from command.step_processor import StepProcessor

class Base:
    """基類：提供共同的初始化和接收功能"""

    def __init__(self, device_id=3, mode = "receive"):
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
            server_port=self.config.get_tc_port(),
            logger=self.logger
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
        """啟動系統"""
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
        """封包接收迴圈"""
        self.logger.info("接收線程已啟動")
        
        while self.running:
            try:
                data, addr = self.network.receive_data()
                if addr and data:
                    # 處理緩衝區，獲取完整幀列表
                    frames = self.network.process_buffer(data)
                    
                    for frame in frames:                    

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
        """處理接收到的封包"""
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
        """處理接收到的封包（覆寫基類方法）"""

        
        # 處理封包(並發送ACK)
        #self.center.process(packet)
        self.center.process_and_ack(packet, addr)
        
class Command(Base):
    """指令下傳介面類：接收+命令雙線程，使用 seq 追蹤命令狀態"""
    
    def __init__(self, device_id=3, mode="command"):
        
        super().__init__(device_id, mode)

        self.packet_def = PacketDefinition()

        self.session_manager = SessionManager(timeout=300)
        self.step_processor = StepProcessor(self.packet_def)
        
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
        # 统一处理所有封包，包括 0F80/0F81
        self.center.process_and_ack(packet, addr)        


# =============命令迴圈=============    

    def _command_loop(self):
        """指令輸入迴圈"""
        
        self._show_help()
        
        while self.running:
            try:
                # 檢查活動會話
                active_session = self.session_manager.get_active_session()
                
                prompt = self.step_processor.get_step_prompt(active_session) if active_session else ""
       
                user_input = input(prompt).strip() # 字串
                
                if not user_input:
                    continue
                
                # 處理會話命令
                if user_input.lower() == 'cancel' and active_session:
                    self.session_manager.remove_session(active_session["cmd_code"])
                    print("已取消當前指令輸入")
                    continue
                
                # 如果有活動會話，處理步驟輸入
                if active_session:
                    success, message, is_complete = self.step_processor.process_step(
                        active_session, user_input
                    )
                    print(message)
                    
                    if is_complete and success:
                        # 發送指令
                        fields = self.step_processor.get_session_fields(active_session)
                        cmd_code = active_session["cmd_code"]
                        
                        description = active_session["definition"].get("description", active_session["cmd_code"])
                        
                        self._send_and_register_command(cmd_code, fields, description)
                        
                        self.session_manager.remove_session(active_session["cmd_code"])

                    continue

                
                # 處理普通命令
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                elif user_input.lower() == 'status':
                    self._show_status()
                else:
                    self._execute_command(user_input)
                        
            except KeyboardInterrupt:
                # 取消活動會話
                active_session = self.session_manager.get_active_session()
                
                if active_session:  
                    self.session_manager.remove_session(active_session["cmd_code"])
                
                    print("\n已取消當前指令輸入")
                
                break
            
            except Exception as e:
                self.logger.info(f"指令處理錯誤: {e}")
        
        self.running = False

    def _execute_command(self, user_input):
        """執行指令"""
        try:

            
            cmd = user_input.upper().split()[0]

            definition = self.packet_def.get_definition(cmd)
            
            if not definition:
                print(f"不支援的指令類型: {cmd}")
                return
            
            if definition.get("reply_type") not in ["查詢", "設定"]:
                print(f"{cmd} 不是可執行命令")
                return
            
            steps = definition.get("steps", [])
            if not steps:
                print(f"錯誤: {cmd} 缺少 steps 定義")
                return
            
            # 判斷是單步還是多步
            is_single_step = len(steps) == 1 and steps[0].get("type") != "confirmation"
            has_params = len(user_input.split()) > 1
            
            if is_single_step:
                # 單步指令：必須帶參數
                if not has_params:
                    format = definition.get("format")
                    example = definition.get("example")
                    print(f"{cmd} 需要參數\n格式: {format}\n範例: {example}")
                    return
                
                # 創建會話，處理單步
                session = self.session_manager.create_session(cmd, definition)
                
                param_str = " ".join(user_input.split()[1:]) # 字串
                
                success, message, is_complete = self.step_processor.process_step(session, param_str)
                
                if success and is_complete:
                    fields = self.step_processor.get_session_fields(session)
                    description = definition.get("description")
                    
                    self._send_and_register_command(cmd, fields, description)
                    self.session_manager.remove_session(cmd)
                else:
                    print(message)
                    self.session_manager.remove_session(cmd)
            else:
                # 無參數查詢指令:確認提示(step1)
                # 多步指令：統一進入互動模式(step1)，忽略參數
                # 創建會話並開始多步驟輸入
                session = self.session_manager.create_session(cmd, definition)


            
        except Exception as e:
            print(f"指令執行錯誤: {e}")
   
    def _send_and_register_command(self, cmd, fields, description):
        """發送指令封包"""
        try:
            seq = self.center.next_seq()

            # 構建封包
            frame = self.center.build(cmd, fields, seq=seq, addr=self.tc_id)
            
            # 發送封包
            if not frame:
                print(f"構建封包失敗: {cmd}")
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


# =============顯示說明=============    

    def _show_help(self):
        """顯示說明"""
        print(f"交通控制系統指令下傳介面 - TC{self.tc_id:03d}")
        print(f"可用指令: help, status, quit")
        
        # 動態獲取可執行命令
        executable_commands = {}
        for cmd, definition in self.packet_def.definitions.items():
            if definition.get("reply_type") in ["查詢", "設定"]:
                executable_commands[cmd] = definition
        
        if executable_commands:
            print(f"\n封包指令:")
            for cmd, definition in sorted(executable_commands.items()):
                format = definition.get("format")
                desc = definition.get("description")
                example = definition.get("example")
                print(f"{desc} - {format}")
                print(f"範例: {example}\n")

        print("\n請輸入指令 (輸入 'help' 查看說明): ")
        
    def _show_status(self):
        """顯示系統狀態"""     
        print(f"\n系統狀態:")
        print(f"  控制器ID: TC{self.tc_id:03d}")

        







