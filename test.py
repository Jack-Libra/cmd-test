import logging
from utils.log_setup import setup_logging
from network.transport import UDPTransport
from network.buffer import FrameBuffer
from utils.packet.packet_parser import PacketParser

def main():
    # 接收模式：輸出到終端 + 檔案
    setup_logging(mode="receive")
    logger = logging.getLogger(__name__)
    
    # 初始化模組
    transport = UDPTransport("0.0.0.0", 5555)
    buffer = FrameBuffer()
    parser = PacketParser()
    
    if not transport.open():
        logger.error("無法開啟傳輸層")
        return
    
    logger.info("=" * 70)
    logger.info("開始監聽號誌控制器（UDP 5555）")
    logger.info("=" * 70)
    
    packet_count = 0
    
    try:
        while True:
            # 1. 接收原始資料
            result = transport.recv()
            if not result:
                continue
            
            data, addr = result
            logger.info(f"\n{'='*70}")
            logger.info(f"收到原始資料 from {addr}: {len(data)} bytes")
            logger.info(f"原始資料 (hex): {data.hex().upper()}")
            
            # 2. 切割完整封包
            packets = buffer.feed(data)
            logger.info(f"切割出 {len(packets)} 個完整封包")
            
            for i, packet in enumerate(packets, 1):

                logger.info(f"封包長度: {len(packet)} bytes")
                logger.info(f"封包內容 (hex): {packet.hex().upper()}")
                
                # 格式化顯示
                hex_str = packet.hex().upper()
                formatted_hex = ' '.join(hex_str[j:j+2] for j in range(0, len(hex_str), 2))
                logger.info(f"格式化顯示: {formatted_hex}")
                
                # 直接解析（解析器會處理所有驗證和識別）
                try:
                    parsed = parser.parse(packet)
                    if parsed:
                        logger.info(f"解析成功:")
                        logger.info(f"   類型: {parsed.get('type', 'UNKNOWN')}")
                        logger.info(f"   命令: {parsed.get('cmd', 'UNKNOWN')}")
                        logger.info(f"   序號: {parsed.get('seq', 'N/A')}")
                        logger.info(f"   位址: 0x{parsed.get('addr', 0):04X}")
                        
                        # 顯示所有欄位
                        for key, value in parsed.items():
                            if key not in ['type', 'cmd', 'seq', 'addr']:
                                logger.info(f"   {key}: {value}")
                    else:
                        logger.warning("解析返回 None")
                
                except Exception as e:
                    logger.error(f"解析失敗: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                
                logger.info("-" * 70)

    except KeyboardInterrupt:
        logger.info(f"收到中斷信號")
        logger.info(f"總共接收並顯示了 {packet_count} 個封包")
        logger.info("正在關閉...")
    except Exception as e:
        logger.error(f"程式異常: {e}", exc_info=True)
    finally:
        transport.close()
        logger.info("程式已結束")

if __name__ == "__main__":
    main()