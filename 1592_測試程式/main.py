"""
感應號誌主程式
"""
import time
from utils.tc_core import *
from utils.tc_config import TCConfig
from utils.tc_network import TCNetwork
from utils.tc_protocol import TrafficControlProtocol

def main():
    """程式進入點"""
    config = TCConfig(device_id=3)

    tc_id = config.get_tc_id()
    if isinstance(tc_id, str) and tc_id.startswith('TC'):
        tc_id = int(tc_id.replace('TC', ''))
    else:
        tc_id = int(tc_id)

    # 初始化網路
    network = TCNetwork(
        local_ip=config.get_transserver_ip(),
        local_port=config.get_transserver_port(),
        server_ip=config.get_tc_ip(),
        server_port=config.get_tc_port()
    )
    
    protocol = TrafficControlProtocol(network=network)
    protocol.set_tc_id(tc_id)

    log_info(f"控制器ID: {tc_id}")
    log_info(f"控制器地址: {config.get_tc_ip()}:{config.get_tc_port()}")

    # 開啟網路連接
    if not network.open():
        log_error("開啟 UDP 連接失敗")
        return

    try:
        log_info("開始接收數據，按 Ctrl+C 結束...")
        while True:
            data, addr = network.receive_data()
            if addr and data:
                packets = network.process_buffer(data)
                for packet in packets:
                    network.process_packet(packet)
            time.sleep(0.01)
    except KeyboardInterrupt:
        log_info("程式已手動停止")
    finally:
        network.close()

if __name__ == "__main__":
    main()
