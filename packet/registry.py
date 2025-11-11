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
    
    def __init__(self):
        self.logger = get_logger()
        self.definitions = DefinitionRegistry()
        self.parser = DataDrivenParser(self.definitions)
        self.builder = DataDrivenBuilder(self.definitions)
        self.processor = PacketProcessor(self.definitions)
        
        self.seq = 0
        self.seq_lock = threading.Lock()

    def parse(self, packet: bytes):
        """解析封包"""
        
        result = self.parser.parse(packet)
        if result:
            self.logger.info("="*60)
            self.logger.info("封包解析結果:"+"\n")
            for key, value in result.items():
                self.logger.info(f"{key}: {value}"+"\n")
            self.logger.info("="*60+"\n")
        else:
            #frame_hex = binascii.hexlify(packet).decode('ascii')
            #self.logger.error(f"封包解析失敗{frame_hex}")
            #self.logger.error("="*60+"\n")
            return 
        
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
        command = packet.get("指令", "")
        if not command:
            command = packet.get("command", "")
        
        # 排除回應封包（0F80/0F81）不發送ACK
        if command in ["0F80", "0F81", "設定/查詢回報（成功）", "設定/查詢回報（失敗）"]:
            logger.debug(f"跳過ACK: {command} 為回應封包，不需要發送ACK")
            return True

        # 如果需要ACK，發送ACK
        if not packet.get("needs_ack", False):
            return True
        
        ack_frame = self.create_ack(packet["seq"], packet["addr"])
        
        if not ack_frame:
            logger.error("ACK封包創建失敗")
            return False
        
        if not addr:
            logger.error("地址無效，無法發送ACK")
            return False
        
        if network.send_data(ack_frame):
            logger.debug(f"發送ACK: Seq={packet['seq']}, TC_ID={packet['addr']}")
            return True
        else:
            logger.error("發送ACK失敗")
            return False


