"""
封包處理註冊中心
統一管理解析器、構建器、處理器
"""

import threading
from packet.packet_parser import PacketParser
from packet.packet_builder import PacketBuilder
from packet.packet_processor import PacketProcessor
from utils import AckFrame
from config.log_setup import get_logger
import binascii

class PacketCenter:
    """封包處理註冊中心"""
    
    def __init__(self, mode="receive"):
        self.logger = get_logger(f"tc.{mode}")
        self.parser = PacketParser(mode=mode)
        self.builder = PacketBuilder()
        self.processor = PacketProcessor(mode=mode)
        
        self.seq = 0
        self.seq_lock = threading.Lock()
    
    def parse(self, packet):
        """解析封包"""
        
        return self.parser.parse(packet)
    
    def build(self, cmd_code, fields, seq=1, addr=0):
        """構建封包"""
        return self.builder.build(cmd_code, fields, seq, addr)
    
    def process(self, packet):
        """處理封包"""
        self.processor.process(packet)
    
    def create_ack(self, seq, addr):
        """創建ACK封包"""
        return AckFrame.encode(seq, addr)
    
    def next_seq(self):
        """獲取下一個序列號（線程安全）"""
        with self.seq_lock:
            self.seq = (self.seq + 1) & 0xFF
            return self.seq

    def process_and_ack(self, packet, network, addr, logger):
        """處理封包並發送ACK"""
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
            logger.info(f"{'='*60}")
            logger.info(f"發送ACK: Seq=0x{packet['序列號']:02X}, ")
            logger.info(f"TC_ID={packet['號誌控制器ID']:03d}, ")
            logger.info(f"目標={addr[0]}:{addr[1]}, ")
            logger.info(f"封包={ack_hex}, ")
            logger.info(f"回應封包={command}")
            logger.info(f"{'='*60}")
        except Exception as e:
            logger.error(f"發送ACK失敗: {e}")





