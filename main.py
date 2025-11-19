"""
交通控制系統主程式

"""
import argparse
from config.network import UDPTransport
from config.config import TCConfig
from config.log_setup import setup_logging
from mode import Receive, Command



def main():
    """程式入口"""
    parser = argparse.ArgumentParser(description='交通控制系統')
    
    parser.add_argument(
        '-m',
        choices=['receive', 'command'],
        default='command',
        help='運行模式: receive=只接收, command=命令模式'
    )
    
    args = parser.parse_args()
    
    # 日誌實例
    logger = setup_logging(log_file=f"{args.m}.log", mode=args.m)    
    
    # 網絡實例
    network=UDPTransport(
        local_ip=TCConfig(3).get_transserver_ip(),
        local_port=TCConfig(3).get_transserver_port(),
        server_ip=TCConfig(3).get_tc_ip(),
        server_port=TCConfig(3).get_tc_port(),
        logger=logger
    )
    
    if args.m == 'receive':
        # 接收模式（只接收數據）
        receiver = Receive(device_id=3, mode="receive", network=network, logger=logger)
        
        if not receiver.start():
            print("啟動接收模式失敗")
            return

    else:   
        # 命令模式（接收+命令雙線程）
        interface = Command(device_id=3, mode="command", network=network, logger=logger)
        
        if not interface.start():
            print("啟動命令模式失敗")
            return


if __name__ == "__main__":
    main()