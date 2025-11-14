"""
交通控制系統主程式

"""
import argparse
from mode import Command, Receive

def main():
    """程式入口"""
    parser = argparse.ArgumentParser(description='交通控制系統')
    
    parser.add_argument(
        '--mode',
        choices=['receive', 'command'],
        default='command',
        help='運行模式: receive=只接收, command=命令模式'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'receive':
        # 接收模式（只接收數據）
        receiver = Receive(device_id=3, mode="receive")
        
        if not receiver.start():
            print("啟動接收模式失敗")
            return

    else:   
        # 命令模式（接收+命令雙線程）
        interface = Command(device_id=3, mode="command")
        
        if not interface.start():
            print("啟動命令模式失敗")
            return


if __name__ == "__main__":
    main()