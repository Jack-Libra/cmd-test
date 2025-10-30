import logging
from utils.log_setup import setup_logging
from network.transport import UDPTransport
from network.buffer import FrameBuffer
from utils.packet.packet_parser import PacketParser
from utils.packet.packet_processor import PacketProcessor
from utils.packet.packet_builder import PacketBuilder
from utils.config import LISTEN_HOST, LISTEN_PORT

def main():
    # 接收模式：輸出到終端 + 檔案
    setup_logging(mode="receive")
    logger = logging.getLogger(__name__)
    
    # 初始化模組
    transport = UDPTransport(LISTEN_HOST, LISTEN_PORT)
    buffer = FrameBuffer()
    parser = PacketParser()
    processor = PacketProcessor("./data")
    
    if not transport.open():
        logger.error("無法開啟傳輸層")
        return
    
    logger.info("=" * 50)
    logger.info(f"開始監聽號誌控制器（UDP {LISTEN_PORT}）")
    logger.info("=" * 50)
    
    try:
        while True:
            # 1. 接收原始資料
            result = transport.recv()
            if not result:
                continue
            
            data, addr = result
            logger.info(f"收到資料 from {addr}: {len(data)} bytes")
            
            # 2. 切割完整封包
            packets = buffer.feed(data)
            
            for packet in packets:
                logger.debug(f"完整封包: {packet.hex().upper()}")
                
                # 3. 解析封包
                parsed = parser.parse(packet)
                if not parsed:
                    logger.warning("無法解析封包")
                    continue
                
                # 4. 處理封包
                processor.process(parsed)
                
                # 5. 發送 ACK
                ack = PacketBuilder.build_ack(parsed['seq'], parsed['addr'])
                if transport.send(ack, addr):
                    logger.info(f"已發送 ACK (seq={parsed['seq']}, addr=0x{parsed['addr']:04X})")
                else:
                    logger.error(f"發送 ACK 失敗")
    
    except KeyboardInterrupt:
        logger.info("\n收到中斷訊號，正在關閉...")
    except Exception as e:
        logger.error(f" 程式異常: {e}", exc_info=True)
    finally:
        transport.close()
        logger.info("程式已關閉")

if __name__ == "__main__":
    main()