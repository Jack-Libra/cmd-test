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
        choices=['receive', 'interactive'],
        default='interactive',
        help='運行模式: receive=只接收, interactive=交互式'
    )
    parser.add_argument(
        '--device-id',
        type=int,
        default=3,
        help='設備ID（默認: 3）'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'receive':
        # 簡單接收模式（只接收數據）
        receiver = Receive(device_id=args.device_id)
        if receiver.start():
            receiver.run()
    else:
        # 交互式模式（使用 Command 類）
        interface = Command(device_id=args.device_id)
        
        if not interface.start():
            return
        
        try:
            # 等待命令線程結束
            interface.command_thread.join()
        except KeyboardInterrupt:
            print("\n程式被中斷")
        finally:
            interface.stop()

if __name__ == "__main__":
    main()