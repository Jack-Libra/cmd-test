import sys


import logging
from utils.log_setup import setup_logging
from network.transport import UDPTransport
from network.buffer import FrameBuffer
from utils.packet.packet_parser import PacketParser
from utils.packet.packet_processor import PacketProcessor
from utils.packet.packet_builder import PacketBuilder

def main():
    # 接收模式：輸出到終端 + 檔案
    setup_logging(mode="receive")
    logger = logging.getLogger(__name__)
    
    # 初始化模組
    transport = UDPTransport("0.0.0.0", 5000)
    buffer = FrameBuffer()
    parser = PacketParser()
    processor = PacketProcessor("./data")
    
    if not transport.open():
        logger.error("無法開啟傳輸層")
        return
    
    logger.info("=" * 50)
    logger.info("開始監聽號誌控制器（UDP 5000）")
    logger.info("=" * 50)
    
    try:
        while True:
            # 1. 接收原始資料
            result = transport.recv()
            if not result:
                continue
            
            data, addr = result
            logger.info(f"📥 收到資料 from {addr}: {len(data)} bytes")
            
            # 2. 切割完整封包
            packets = buffer.feed(data)
            
            for packet in packets:
                logger.debug(f"完整封包: {packet.hex().upper()}")
                
                # 3. 解析封包
                parsed = parser.parse(packet)
                if not parsed:
                    logger.warning("⚠️  無法解析封包")
                    continue
                
                # 4. 處理封包
                processor.process(parsed)
                
                # 5. 根據 reply_type 決定是否回覆 ACK
                reply_type = parsed.get('reply_type', 'none')
                
                if reply_type == 'ack':
                    # 查詢回報：回覆 ACK
                    ack = PacketBuilder.build_ack(parsed['seq'], parsed['addr'])
                    if transport.send(ack, addr):
                        logger.info(f"✅ 已回覆 ACK (seq={parsed['seq']}, addr=0x{parsed['addr']:04X})")
                    else:
                        logger.error(f"❌ 回覆 ACK 失敗")
                elif reply_type == 'none':
                    # 主動回報：不回覆 ACK
                    logger.debug(f"📋 主動回報 {parsed.get('cmd')}，不需回覆 ACK")
                elif parsed.get('type') == 'ACK':
                    # 收到設備的 ACK（對我們之前命令的確認），不需再回覆
                    logger.info(f"📩 收到設備 ACK 確認 (seq={parsed['seq']}, addr=0x{parsed['addr']:04X})")
    
    except KeyboardInterrupt:
        logger.info("\n🛑 收到中斷信號，正在關閉...")
    except Exception as e:
        logger.error(f"❌ 程式異常: {e}", exc_info=True)
    finally:
        transport.close()
        logger.info("程式已結束")

if __name__ == "__main__":
    main()