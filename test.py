import logging
import json
import time
import traceback
import socket
from pathlib import Path
from utils.log_setup import setup_logging
from network.transport import UDPTransport
from network.buffer import FrameBuffer
from utils.packet.packet_parser import PacketParser
from utils.packet.packet_processor import PacketProcessor
from utils.packet.packet_builder import PacketBuilder
from utils.config import TRAFFIC_CONTROLLERS
from utils.core import Ack, Nak, xor_checksum

COMMAND_QUEUE_FILE = "./command_queue.json"
QUEUE_CHECK_INTERVAL = 0.5

seq = 0
_DEFAULT_ADDR = 0x0003


logger = logging.getLogger(__name__)

config = TRAFFIC_CONTROLLERS['TC003']
pending_commands: dict[int, dict] = {}
def get_next_seq() -> int:
    """獲取下一個 seq 值（自動遞增）"""
    global seq
    seq = (seq % 255) + 1  # 循環 1-255
    return seq

def read_and_clear_queue() -> list:
    """讀取並清空命令隊列"""
    queue_file = Path(COMMAND_QUEUE_FILE)
    if not queue_file.exists():
        return []
    
    try:
        with open(queue_file, 'r', encoding='utf-8') as f:
            queue = json.load(f)
        
        # 清空文件
        with open(queue_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        return queue
    except Exception as e:
        logging.getLogger(__name__).debug(f"讀取命令隊列失敗: {e}")
        return []

def process_command_queue(logger):
    """處理命令隊列中的命令"""
    commands = read_and_clear_queue()
    
    if not commands:
        return
    
    
    builder = PacketBuilder()
    
    for cmd_dict in commands:
        
        try:
            cmd = cmd_dict['cmd']
            params = cmd_dict['params']
            seq = get_next_seq()

            logger.info(f"處理命令: {cmd} {params}")
            
            # 建立封包
            result = builder.build(cmd, params, seq=seq, addr=_DEFAULT_ADDR)
            if result[0] is None:
                logger.error(f"建立封包失敗: {result[1]}")
                continue
            
            packet, cmd_desc, info_bytes = result
            
            # 格式化顯示封包
            hex_str = packet.hex().upper()
            formatted_hex = ' '.join(hex_str[j:j+2] for j in range(0, len(hex_str), 2))
            logger.info(f"封包 (hex): {formatted_hex}")
            logger.info(f"命令描述: {cmd_desc}")
            
            # 發送
            try:
                temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                temp_sock.sendto(packet, (config['TC_ip'], config['TC_port']))
                temp_sock.close()
                logger.info(f"發送成功: {cmd_desc}")
            except Exception as e:
                logger.error(f"發送失敗: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"處理命令失敗: {e}", exc_info=True)

def main():
    # 接收模式：輸出到終端 + 檔案
    setup_logging(mode="receive")
    
    # 初始化模組
    recv_transport = UDPTransport(config['TransServer_ip'], config['TransServer_port'])
    buffer = FrameBuffer()
    parser = PacketParser()
    processor = PacketProcessor("./data")
    
    if not recv_transport.open():
        logger.error("無法開啟接收傳輸層")
        return
    
    logger.info("=" * 70)
    logger.info("開始監聽號誌控制器")
    logger.info(f"接收端口: {config['TransServer_port']} (綁定)")
    logger.info(f"發送目標: {config['TC_ip']}:{config['TC_port']} (使用臨時端口)")
    logger.info(f"自動設定: seq (自動遞增), addr=0x{_DEFAULT_ADDR:04X} (固定)")
    logger.info("=" * 70)
    
    packet_count = 0
    last_queue_check = time.time()
    
    try:
        while True:
            # 定期檢查命令隊列並發送
            current_time = time.time()
            if current_time - last_queue_check >= QUEUE_CHECK_INTERVAL:
                process_command_queue()
                last_queue_check = current_time
                       
            # 接收原始資料
            result = recv_transport.recv()
            if not result:
                continue
            
            data, addr = result
            logger.info(f"{'='*70}")
            logger.info(f"收到原始資料 from {addr}: {len(data)} bytes")
            logger.info(f"原始資料 (hex): {data.hex().upper()}")
            
            # 切割完整封包
            packets = buffer.feed(data)
            
            for packet in packets:
                try:
                    # 驗證校驗和
                    if not verify_checksum(packet):
                        logger.error("❌ 封包校驗和錯誤")
                        continue
                    
                    # 解析封包
                    parsed = parser.parse(packet)
                    if not parsed:
                        logger.warning("⚠️  無法解析封包")
                        continue
                    
                    packet_seq = parsed.get('seq')
                    packet_addr = parsed.get('addr')
                    packet_type = parsed.get('type')
                    packet_cmd = parsed.get('指令')
                    reply_type = parsed.get('回覆類型', '')
                    
                    # 格式化顯示
                    hex_str = packet.hex().upper()
                    formatted_hex = ' '.join(hex_str[j:j+2] for j in range(0, len(hex_str), 2))
                    logger.info(f"格式化顯示: {formatted_hex}")
                    
                    # 處理 ACK 封包
                    if packet_type == "ACK":
                        logger.info(f"📩 收到 ACK (seq={packet_seq}, addr=0x{packet_addr:04X})")
                        
                        if packet_seq in pending_commands:
                            pending_commands[packet_seq]["ack_received"] = True
                            pending_commands[packet_seq]["addr"] = packet_addr
                            logger.info(f"✅ ACK 驗證通過 (seq={packet_seq})")
                        else:
                            logger.warning(f"⚠️  收到未預期的 ACK (seq={packet_seq})")
                    
                    # 處理查詢回報封包（需要回覆 ACK 的類型）
                    elif reply_type == "查詢回報":
                        logger.info(f"📥 收到查詢回報: {packet_cmd} (seq={packet_seq}, addr=0x{packet_addr:04X})")
                        
                        # 檢查 seq 是否在待處理命令中
                        if packet_seq in pending_commands:
                            cmd_info = pending_commands[packet_seq]
                            
                            # 檢查是否為錯誤回報
                            if packet_cmd == "0F81":
                                logger.error(f"❌ 收到錯誤回報: {packet_cmd} (seq={packet_seq})")
                                error_code = parsed.get("error_code", 0)
                                
                                # 發送 NACK 回覆（使用相同的 seq）
                                nak_packet = Nak.encode(packet_seq, packet_addr, error_code)
                                if send_packet(nak_packet, config['TC_ip'], config['TC_port']):
                                    logger.info(f"❌ 已回覆 NACK (seq={packet_seq}, err=0x{error_code:02X})")
                                else:
                                    logger.error(f"❌ 回覆 NACK 失敗")
                                
                                # 清除待處理命令
                                del pending_commands[packet_seq]
                            else:
                                # 正常回報，標記已收到
                                cmd_info["reply_received"] = True
                                logger.info(f"✅ 回報封包驗證通過 (seq={packet_seq}, cmd={packet_cmd})")
                                
                                # 處理封包內容
                                info = processor.process(parsed)
                                if info:
                                    logger.info("=== 封包解析結果 ===")
                                    for key, value in info.items():
                                        logger.info(f"{key}: {value}")
                                
                                # 檢查是否已收到 ACK 和回報
                                if cmd_info["ack_received"] and cmd_info["reply_received"]:
                                    # 發送 ACK 回覆（使用相同的 seq，不遞增）
                                    ack_packet = Ack.encode(packet_seq, packet_addr)
                                    
                                    if send_packet(ack_packet, config['TC_ip'], config['TC_port']):
                                        logger.info(f"✅ 已回覆 ACK (seq={packet_seq}, addr=0x{packet_addr:04X})")
                                    else:
                                        logger.error(f"❌ 回覆 ACK 失敗")
                                    
                                    # 清除待處理命令
                                    del pending_commands[packet_seq]
                                else:
                                    logger.info(f"⏳ 等待 ACK 封包 (seq={packet_seq})")
                        else:
                            logger.warning(f"⚠️  收到未預期的查詢回報 (seq={packet_seq}, cmd={packet_cmd})")
                        
                        packet_count += 1
                    
                    # 處理主動回報（不需要回覆）
                    elif reply_type == "主動回報":
                        logger.info(f"📋 收到主動回報: {packet_cmd} (seq={packet_seq})")
                        info = processor.process(parsed)
                        if info:
                            logger.info("=== 封包解析結果 ===")
                            for key, value in info.items():
                                logger.info(f"{key}: {value}")
                        packet_count += 1
                    
                    else:
                        logger.debug("未定義的封包類型，已忽略")
                
                except Exception as e:
                    logger.debug(f"封包解析異常（可能為未定義類型）: {e}")
                    logger.debug(traceback.format_exc())
                
                logger.info("=" * 70)
    
    except KeyboardInterrupt:
        logger.info(f"收到中斷信號")
        logger.info(f"總共接收並顯示了 {packet_count} 個封包")
        logger.info("正在關閉...")
    except Exception as e:
        logger.error(f"程式異常: {e}", exc_info=True)
    finally:
        recv_transport.close()
        logger.info("程式已結束")

if __name__ == "__main__":
    main()