"""
封包處理註冊中心
統一管理解析器、構建器、處理器
"""

import logging
import threading
from typing import Dict, Optional
from .definitions.registry import DefinitionRegistry
from .parser.data_driven_parser import DataDrivenParser
from .builder.data_driven_builder import DataDrivenBuilder
from .processor.packet_processor import PacketProcessor
from core.frame import AckFrame
from log_config.setup import get_logger
import binascii

class PacketRegistry:
    """封包處理註冊中心"""
    
    def __init__(self, mode: str = "receive"):
        self.logger = get_logger(f"tc.{mode}")
        self.definitions = DefinitionRegistry()
        self.parser = DataDrivenParser(self.definitions, mode=mode)
        self.builder = DataDrivenBuilder(self.definitions)
        self.processor = PacketProcessor(self.definitions, mode=mode)
        
        self.seq = 0
        self.seq_lock = threading.Lock()
    
    def parse(self, packet: bytes):
        """解析封包"""
        
        return self.parser.parse(packet)
    
    def build(self, cmd_code: str, fields: Dict, seq: int = 1, addr: int = 0):
        """構建封包"""
        return self.builder.build(cmd_code, fields, seq, addr)
    
    def process(self, packet: Dict):
        """處理封包"""
        self.processor.process(packet)
    
    def create_ack(self, seq: int, addr: int):
        """創建ACK封包"""
        return AckFrame.encode(seq, addr)
    
    def get_definition(self, cmd_code: str):
        """獲取封包定義"""
        return self.definitions.get_definition(cmd_code)
    
    def register_definition(self, cmd_code: str, definition: Dict):
        """註冊新封包定義"""
        self.definitions.register_definition(cmd_code, definition)
        self.logger.info(f"註冊新封包定義: {cmd_code}")

    def next_seq(self):
        """獲取下一個序列號（線程安全）"""
        with self.seq_lock:
            self.seq = (self.seq + 1) & 0xFF
            return self.seq

    def process_and_ack(self, packet: Dict, network, addr: tuple, logger):
        """處理封包並發送ACK（如果需要）"""
        if not packet:
            return False
        
        # 處理封包
        self.process(packet)

        # 獲取命令碼
        command = packet.get("指令編號")

        

        # 如果需要ACK，發送ACK
        if not packet.get("needs_ack", False):
            return True
        
        ack_frame = self.create_ack(packet["序列號"], packet["號誌控制器ID"])
        
        try:
            network.send_data(ack_frame, addr)
            ack_hex = binascii.hexlify(ack_frame).decode('ascii').upper()
            logger.info(
                f"發送ACK: Seq=0x{packet['序列號']:02X}, "
                f"TC_ID={packet['號誌控制器ID']:03d}, "
                f"目標={addr[0]}:{addr[1]}, "
                f"封包={ack_hex}, "
                f"回應封包={command}"
            )
        except Exception as e:
            logger.error(f"發送ACK失敗: {e}")


