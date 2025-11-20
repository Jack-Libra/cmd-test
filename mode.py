# command.py

"""
交通控制系統指令下傳介面
基類架構：Base -> Command, Receive
"""

import threading
import time
from typing import Optional
import binascii

from config.config import TCConfig
from config.log_setup import get_logger
from config.network import NetworkTransport

from packet.center import PacketCenter

from command.session_manager import SessionManager
from command.step_processor import StepProcessor


class Base:
    """基類：提供共同的初始化和接收功能"""

    def __init__(self, device_id=3, mode = "receive", network: Optional[NetworkTransport] = None, logger=None):
        
        self.mode = mode
        
        self.device_id = device_id     
        
        self.logger = logger if logger else get_logger(f"tc.{mode}")
        
        self.config = TCConfig(device_id)
        
        self.tc_id = device_id
        
        # 初始化網路
        self.network = network
        
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
                        self.center.process(self.center.parse(frame), addr)
                
                time.sleep(0.01)
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"封包接收錯誤: {e}", exc_info=True)
                time.sleep(0.1)
        
        self.logger.info("接收線程已停止")
    


class Receive(Base):
    """接收模式：只接收數據，不發送命令"""
    def __init__(self, device_id=3, mode: str = "receive" , network: NetworkTransport = None, logger=None):
        super().__init__(device_id, mode, network, logger)

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
            self.logger.info("退出接收模式")
        
        finally:
            self.stop()
        
        return True
    
        
class Command(Base):
    """指令下傳介面類：接收+命令雙線程，使用 seq 追蹤命令狀態"""
    
    def __init__(self, device_id=3, mode="command", network: NetworkTransport = None, logger=None):
        
        super().__init__(device_id, mode, network, logger)

        self.packet_def = self.center.packet_def

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
            self.command_thread.join()
        except KeyboardInterrupt:
            self.logger.info("退出命令模式")
        finally:
            self.stop()
        
        return True

# =============命令迴圈=============    

    def _command_loop(self):
        """指令輸入迴圈"""
        self.logger.info("命令模式已啟動")
        self._show_help()
        print("輸入指令進入會話")
        
        while self.running:
            try:
                # 檢查活動會話
                active_session = self.session_manager.get_active_session()
                
                prompt = self.step_processor.get_step_prompt(active_session) if active_session else ""
       
                user_input = input(prompt).strip() # 字串
                
                if not user_input:
                    continue
                
                # 處理會話命令
                if user_input.lower() == 'q' and active_session:
                    self.session_manager.remove_session(active_session.cmd_code)
                    print("取消當前指令輸入")
                    continue
                
                # 如果有活動會話，處理步驟輸入
                if active_session:
                    
                    success, message, is_complete = self.step_processor.process_step(active_session, user_input)
                    
                    # process_step 返回
                    if message:
                        print(message)
                    
                    if is_complete and success:
                        
                        # 發送指令
                        
                        cmd_code = active_session.cmd_code
                        
                        description = active_session.definition.get("description", active_session.cmd_code)
                        
                        self.center.send_command(cmd_code, active_session.fields, description)
                        
                        self.session_manager.remove_session(active_session.cmd_code)
                    
                    # 輸入失敗 重新輸入
                    continue

                
                # 處理普通命令
                if user_input.lower() == 'q':
                    self.logger.info("退出命令模式")
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                elif user_input.lower() == 'status':
                    self._show_status()
                else:
                    self._execute_command(user_input)
                        
            except KeyboardInterrupt:
                self.logger.info("退出命令模式")
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
                print(f"尚未實作指令: {cmd}")
                return
            
            if definition.get("reply_type") not in ["查詢", "設定"]:
                print(f"{cmd} 不是可執行命令")
                return
            
            # 統一處理：所有指令都創建會話，忽略參數
            # 後續步驟由循環統一處理
            self.session_manager.create_session(cmd, definition)
            
        except Exception as e:
            print(f"指令執行錯誤: {e}")
   



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
    
        
    def _show_status(self):
        """顯示系統狀態"""     
        print(f"\n系統狀態:")
        print(f"  控制器ID: TC{self.tc_id:03d}")

        







