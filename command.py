import logging
import sys
from utils.log_setup import setup_logging, get_command_logger
from network.transport import UDPTransport
from utils.packet.packet_builder import PacketBuilder

def print_usage():
    """顯示使用說明"""
    print("=" * 60)
    print("交通控制器命令工具")
    print("=" * 60)
    print("\n用法: python command.py <target_ip> <target_port> <command> [args...]")
    print("\n可用命令:")
    print("  5f40  查詢控制策略")
    print("        python command.py 192.168.1.100 5000 5f40 <seq> <addr>")
    print("        範例: python command.py 192.168.1.100 5000 5f40 1 0x1230")
    print()
    print("  5f10  設定控制策略")
    print("        python command.py 192.168.1.100 5000 5f10 <seq> <addr> <control> <time>")
    print("        範例: python command.py 192.168.1.100 5000 5f10 1 0x1230 0x01 10")
    print()
    print("  5f48  查詢時制計畫")
    print("        python command.py 192.168.1.100 5000 5f48 <seq> <addr>")
    print("        範例: python command.py 192.168.1.100 5000 5f48 1 0x1230")
    print("=" * 60)

def main():
    # 下傳模式：不輸出到終端，只寫檔案
    setup_logging(mode="command")
    logger = logging.getLogger(__name__)  # 只寫檔案
    output = get_command_logger()  # 簡潔終端輸出
    
    if len(sys.argv) < 4:
        print_usage()
        return
    
    try:
        target_ip = sys.argv[1]
        target_port = int(sys.argv[2])
        cmd = sys.argv[3].lower()
    except (ValueError, IndexError):
        output.error("❌ 參數錯誤")
        print_usage()
        return
    
    transport = UDPTransport()
    if not transport.open():
        logger.error("無法開啟傳輸層")
        output.error("❌ 無法開啟網路連線")
        return
    
    try:
        packet = None
        cmd_desc = ""
        
        if cmd == "5f40":
            # 查詢控制策略
            if len(sys.argv) < 6:
                output.error("❌ 參數不足")
                print_usage()
                return
            seq = int(sys.argv[4])
            addr = int(sys.argv[5], 16) if sys.argv[5].startswith('0x') else int(sys.argv[5])
            packet = PacketBuilder.build_5f40(seq, addr)
            cmd_desc = f"5F40 查詢控制策略 (seq={seq}, addr=0x{addr:04X})"
        
        elif cmd == "5f10":
            # 設定控制策略
            if len(sys.argv) < 8:
                output.error("❌ 參數不足")
                print_usage()
                return
            seq = int(sys.argv[4])
            addr = int(sys.argv[5], 16) if sys.argv[5].startswith('0x') else int(sys.argv[5])
            control = int(sys.argv[6], 16) if sys.argv[6].startswith('0x') else int(sys.argv[6])
            effect_time = int(sys.argv[7])
            packet = PacketBuilder.build_5f10(seq, addr, control, effect_time)
            cmd_desc = f"5F10 設定控制策略 (seq={seq}, addr=0x{addr:04X}, control=0x{control:02X}, time={effect_time}分)"
        
        elif cmd == "5f48":
            # 查詢時制計畫
            if len(sys.argv) < 6:
                output.error("❌ 參數不足")
                print_usage()
                return
            seq = int(sys.argv[4])
            addr = int(sys.argv[5], 16) if sys.argv[5].startswith('0x') else int(sys.argv[5])
            packet = PacketBuilder.build_5f48(seq, addr)
            cmd_desc = f"5F48 查詢時制計畫 (seq={seq}, addr=0x{addr:04X})"
        
        else:
            output.error(f"❌ 未知命令: {cmd}")
            print_usage()
            return
        
        # 記錄到檔案（詳細）
        logger.info(f"發送命令: {cmd_desc} 到 {target_ip}:{target_port}")
        logger.debug(f"封包內容: {packet.hex().upper()}")
        
        # 輸出到終端（簡潔）
        output.info(f"📤 發送命令: {cmd_desc}")
        output.info(f"   目標: {target_ip}:{target_port}")
        output.info(f"   封包: {packet.hex().upper()}")
        
        # 發送
        if transport.send(packet, (target_ip, target_port)):
            logger.info("發送成功")
            output.info("✅ 發送成功")
        else:
            logger.error("發送失敗")
            output.error("❌ 發送失敗")
    
    except ValueError as e:
        logger.error(f"參數格式錯誤: {e}")
        output.error(f"❌ 參數格式錯誤: {e}")
    except Exception as e:
        logger.error(f"執行失敗: {e}", exc_info=True)
        output.error(f"❌ 執行失敗: {e}")
    finally:
        transport.close()

if __name__ == "__main__":
    main()