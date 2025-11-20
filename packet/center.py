"""
封包處理中心
統一管理解析器、構建器、處理器
"""

import threading
import binascii
from typing import Tuple, Optional, Set

from packet.packet_parser import PacketParser
from packet.packet_builder import PacketBuilder
from packet.packet_processor import PacketProcessor
from packet.packet_definition import PacketDefinition

from utils import encode
from config.log_setup import get_logger



class PacketCenter:
    """封包處理中心"""
    
    def __init__(self, mode="receive", network=None, config=None, tc_id=None, logger=None):
        
        self.logger = get_logger(f"tc.{mode}")
        
        self.packet_def = PacketDefinition()
        
        # 將 packet_def 注入到各個組件
        self.parser = PacketParser(mode=mode, packet_def=self.packet_def)
        self.builder = PacketBuilder(packet_def=self.packet_def)
        self.processor = PacketProcessor(mode=mode, packet_def=self.packet_def)
        
        self.network = network
        self.config = config  
        self.tc_id = tc_id    
        
        self.seq = 0
        self.pending_seqs: Set[int] = set()

        self.seq_lock = threading.Lock()

    def parse(self, packet):
        """解析封包"""     
        return self.parser.parse(packet)
    
    def build(self, cmd_code, fields, seq=1, addr=0):
        """構建封包"""
        return self.builder.build(cmd_code, fields, seq, addr)
    
    def next_seq(self):
        """獲取下一個序列號（線程安全）"""
        with self.seq_lock:
            self.seq = (self.seq + 1) & 0xFF
            return self.seq

    def send(self, frame: bytes, addr: Tuple[str, int], description: str = "") -> bool:
        """
        發送封包
        
        Args:
            frame: 封包字節數據
            addr: 發送地址 (ip, port)
            description: 封包描述（用於日誌）
            
        Returns:
            是否發送成功
        """
        if not self.network:
            self.logger.error("網路未初始化")
            return False
        
        try:
            if self.network.send_data(frame, addr):


                frame_hex = binascii.hexlify(frame).decode('ascii').upper()
                self.logger.info("="*60)
                self.logger.info(f"發送地址: {addr[0]}:{addr[1]}")
                if description:
                    self.logger.info(f"描述: {description}")
                self.logger.info(f"封包內容: {frame_hex}")
                self.logger.info("="*60)
                return True
            else:
                self.logger.error("封包發送失敗")
                return False
        except Exception as e:
            self.logger.error(f"發送封包失敗: {e}", exc_info=True)
            return False

    def send_command(self, cmd_code: str, fields: dict, description: str = "") -> Optional[int]:
        """
        發送指令封包 命令線程用
        
        Args:
            cmd_code: 指令碼
            fields: 字段數據
            description: 指令描述
            
        Returns:
            序列號（成功）或 None（失敗）
        """
        if not self.config:
            self.logger.error("配置未初始化")
            return None

        seq = self.next_seq()
        
        # 使用 build 方法構建完整封包（addr 是控制器ID，int類型）
        frame = self.build(cmd_code, fields, seq=seq, addr=self.tc_id)
        
        if frame is None:
            self.logger.error(f"構建封包失敗: {cmd_code}")
            return None
        
        # 獲取發送地址（用於 send 方法）
        addr = (self.config.get_tc_ip(), self.config.get_tc_port())
        
        # 發送封包
        if self.send(frame, addr, f"{description} (SEQ: {seq})"):
            with self.seq_lock:
                self.pending_seqs.add(seq)
            return seq           
        return None

    def process(self, packet, addr):
        """
        處理封包並發送ACK 接收線程用
        
        Args:
            packet: 解析後的封包對象 Packet 類型
            addr: 發送地址 (ip, port)
        """
        if not packet:
            return False

        # 如果是ACK封包，檢查是否對應待確認的seq
        if packet.reply_type == "ACK":
            with self.seq_lock:
                if packet.seq in self.pending_seqs:                   

                    # 在終端顯示ACK信息
                    self.logger.info(f"[ACK] 收到確認: Seq=0x{packet.seq:02X}, TC_ID={packet.tc_id:03d}")
                    self.logger.info(f"封包內容: {packet.raw_packet}")
                    self.logger.info("="*60)
                    
                    self.pending_seqs.remove(packet.seq)
            return True

        # 處理封包
        self.processor.process(packet)

        ack_frame = encode(packet.seq, packet.tc_id, b"")
        
        # 靜默發送ACK（不顯示日誌）
        if self.network:
            self.network.send_data(ack_frame, addr)
            #ack_frame_hex = binascii.hexlify(ack_frame).decode('ascii').upper()
            #self.logger.info("="*60)
            #self.logger.info(f"ACK封包內容: {ack_frame_hex}")
            #self.logger.info(f"發送地址: {addr[0]}:{addr[1]}")
            #self.logger.info(f"對應指令: {packet.cmd_code}")
            #self.logger.info("="*60)

        return True






