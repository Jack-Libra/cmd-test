import json
from pathlib import Path

COMMAND_QUEUE_FILE = "./command_queue.json"

def print_usage():
    """顯示使用說明"""
    print("=" * 60)
    print("交通控制器命令工具")
    print("=" * 60)
    print("\n可用命令:")
    print("  5F40                    - 查詢控制策略")
    print("  5F10 c t                - 設定控制策略 (c=控制碼, t=生效時間)")
    print("  5F48                    - 查詢時制計畫")
    print("  5F1C s p t              - 設定時相或步階變換控制 (s=子時相, p=步階, t=時間)")
    print("\n範例:")
    print("  5F40                    # 查詢控制策略")
    print("  5F10 0x01 5             # 設定控制策略")
    print("  5F48                    # 查詢時制計畫")
    print("  5F1C 1 2 10             # 設定時相變換")
    print("\n注意: seq 和 addr 會自動設定，每次發送 seq 自動遞增")
    print("\n輸入 'quit' 或 'exit' 退出")
    print("=" * 60)

def parse_command(cmd_input: str) -> dict:
    """
    解析指令
    返回: 命令字典或 None
    """
    parts = cmd_input.strip().upper().split()
    
    if not parts:
        return None
    
    cmd = parts[0]
    params = []
    
    # 解析參數
    for param in parts[1:]:
        if param.startswith('0x') or param.startswith('0X'):
            params.append(int(param, 16))
        else:
            try:
                params.append(int(param))
            except ValueError:
                return {"error": f"無效的參數: {param}"}
    
    # 驗證命令
    if cmd not in ["5F40", "5F10", "5F48", "5F1C"]:
        return {"error": f"不支援的命令: {cmd}"}
    
    return {
        "cmd": cmd,
        "params": params,
        "timestamp": None  # test.py 會填入
    }

def write_command_to_queue(cmd_dict: dict) -> bool:
    """將命令寫入隊列文件"""
    try:
        queue_file = Path(COMMAND_QUEUE_FILE)
        
        # 讀取現有隊列
        if queue_file.exists():
            with open(queue_file, 'r', encoding='utf-8') as f:
                queue = json.load(f)
        else:
            queue = []
        
        # 添加新命令
        queue.append(cmd_dict)
        
        # 寫回文件
        with open(queue_file, 'w', encoding='utf-8') as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"寫入命令隊列失敗: {e}")
        return False

def main():
    print_usage()
    
    # 初始化命令隊列文件
    queue_file = Path(COMMAND_QUEUE_FILE)
    if queue_file.exists():
        queue_file.unlink()  # 清除舊的隊列
    queue_file.touch()
    with open(queue_file, 'w', encoding='utf-8') as f:
        json.dump([], f)
    
    print("命令解析器已啟動")
    print("請確保 test.py 正在運行以處理命令")
    
    try:
        while True:
            try:
                # 讀取用戶輸入
                cmd_input = input("請輸入指令: ").strip()
                
                if not cmd_input:
                    continue
                
                # 檢查退出指令
                if cmd_input.lower() in ['quit', 'exit', 'q']:
                    print("退出程式...")
                    break
                
                # 解析指令
                cmd_dict = parse_command(cmd_input)
                if cmd_dict is None:
                    print("無效的命令")
                    continue
                
                if "error" in cmd_dict:
                    print(f"錯誤: {cmd_dict['error']}")
                    continue
                
                # 寫入隊列
                if write_command_to_queue(cmd_dict):
                    print(f"命令已加入隊列: {cmd_dict['cmd']} {cmd_dict['params']}")
                else:
                    print("無法寫入命令隊列")
            
            except KeyboardInterrupt:
                print("收到中斷信號，退出...")
                break
            except Exception as e:
                print(f"錯誤: {e}")
    
    finally:
        # 清理隊列文件
        if queue_file.exists():
            queue_file.unlink()
        print("已關閉命令解析器")

if __name__ == "__main__":
    main()