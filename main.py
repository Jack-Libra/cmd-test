"""
交通控制系統主程式

"""

import time
from config import TCConfig
from network import UDPTransport
from packet import PacketRegistry
from logging.setup import setup_logging, get_logger

def main():
    """程式入口"""
    # 設置日誌
    logger = get_logger()
    
    # 加載配置
    config = TCConfig(device_id=3)
    tc_id = config.get_tc_id()
    if isinstance(tc_id, str) and tc_id.startswith('TC'):
        tc_id = int(tc_id.replace('TC', ''))
    else:
        tc_id = int(tc_id)
    
    # 初始化網路
    network = UDPTransport(
        local_ip=config.get_transserver_ip(),
        local_port=config.get_transserver_port(),
        server_ip=config.get_tc_ip(),
        server_port=config.get_tc_port()
    )
    
    # 初始化封包註冊中心
    registry = PacketRegistry()
    
    logger.info(f"控制器ID: {tc_id}")
    logger.info(f"控制器地址: {config.get_tc_ip()}:{config.get_tc_port()}")
    
    # 開啟網路連接
    if not network.open():
        logger.error("開啟 UDP 連接失敗")
        return
    
    try:
        logger.info("開始接收資料，按 Ctrl+C 結束...")
        while True:
            data, addr = network.receive_data()
            if addr and data:
                # 處理緩衝區，獲取完整幀列表
                frames = network.process_buffer(data)
                
                for frame in frames:
                    # 解析幀，獲取封包
                    packet = registry.parse(frame)
                    
                    if packet:
                        # 處理封包
                        registry.process(packet)
                        
                        # 如果需要ACK，發送ACK
                        if packet.get("needs_ack", False):
                            seq = packet.get("seq", 0)
                            tc_id_val = packet.get("tc_id", tc_id)
                            ack_frame = registry.create_ack(seq, tc_id_val)
                            if ack_frame and addr:
                                network.send_data(ack_frame)
                                logger.debug(f"發送ACK: Seq={seq}, TC_ID={tc_id_val}")
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        logger.info("程式已手動停止")
    except Exception as e:
        logger.error(f"程式錯誤: {e}", exc_info=True)
    finally:
        network.close()

if __name__ == "__main__":
    main()
