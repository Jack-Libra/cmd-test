"""
封包處理中心
統一管理解析器、構建器、處理器
"""

import threading
from packet.packet_parser import PacketParser
from packet.packet_builder import PacketBuilder
from packet.packet_processor import PacketProcessor
from packet.packet_definition import PacketDefinition

from utils import AckFrame
from config.log_setup import get_logger
import binascii


class PacketCenter:
    """封包處理中心"""
    
    def __init__(self, mode="receive", network=None, config=None, tc_id=None, logger=None):
        
        self.logger = get_logger(f"tc.{mode}")
        
        self.packet_def = PacketDefinition()
        
        # 將 packet_def 注入到各個組件
        self.parser = PacketParser(mode=mode, packet_def=self.packet_def)
        self.builder = PacketBuilder(packet_def=self.packet_def)
        self.processor = PacketProcessor(mode=mode, packet_def=self.packet_def)
        
        # 保存 network 和 logger 用於 process_and_ack
        self.network = network

        
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

    def process_and_ack(self, packet, addr):
        """
        處理封包並發送ACK
        
        Args:
            packet: 解析後的封包字典
            addr: 發送地址 (ip, port)
        """
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
            if self.network:
                self.network.send_data(ack_frame, addr)
                ack_hex = binascii.hexlify(ack_frame).decode('ascii').upper()
                log_msg = (
                    f"{'='*60}\n"
                    f"發送ACK: Seq=0x{packet['序列號']:02X}, "
                    f"TC_ID={packet['號誌控制器ID']:03d}, "
                    f"目標={addr[0]}:{addr[1]}, "
                    f"封包={ack_hex}, "
                    f"回應封包={command}\n"
                    f"{'='*60}"
                )
                #self.logger.info(log_msg)
        except Exception as e:
            self.logger.error(f"發送ACK失敗: {e}")
        
        return True





