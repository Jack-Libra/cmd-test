import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(mode: str = "receive", log_dir: str = "./logs"):
    """
    設定日誌系統
    
    Args:
        mode: "receive" (接收模式) 或 "command" (下傳模式)
        log_dir: 日誌檔案目錄
    """
    # 建立日誌目錄
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 日誌檔案路徑
    log_file = log_path / "traffic_control.log"
    
    # 根日誌器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 清除既有的 handlers（避免重複）
    root_logger.handlers.clear()
    
    # 檔案處理器（所有模式都輸出到檔案）
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 終端處理器（根據模式決定）
    if mode == "receive":
        # 接收模式：輸出到終端
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    elif mode == "command":
        # 下傳模式：不輸出到終端（避免干擾）
        # 只有檔案處理器，終端保持乾淨
        pass
    
    # 記錄啟動資訊
    root_logger.info("=" * 60)
    root_logger.info(f"日誌系統啟動 - 模式: {mode.upper()}")
    root_logger.info(f"日誌檔案: {log_file.absolute()}")
    root_logger.info("=" * 60)


def get_command_logger():
    """
    為下傳模式建立專用的簡潔輸出 logger
    只在需要時輸出到終端（例如命令結果）
    """
    logger = logging.getLogger("command_output")
    logger.setLevel(logging.INFO)
    
    # 移除繼承的 handlers
    logger.propagate = False
    
    # 只輸出到終端
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')  # 簡潔格式
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger