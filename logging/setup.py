# logging/setup.py
"""
日誌配置
"""

import logging
import os
from pathlib import Path

def setup_logging(log_dir: str = "logs", log_file: str = "traffic_control.log"):
    """設置日志系統"""
    # 創建日誌目錄
    Path(log_dir).mkdir(exist_ok=True)
    
    # 配置日誌格式
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 文件處理器
    log_path = os.path.join(log_dir, log_file)
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    file_handler.setLevel(logging.INFO)
    
    # 控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    console_handler.setLevel(logging.INFO)
    
    # 配置根日誌器
    logger = logging.getLogger("tc")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str = "tc"):
    """獲取日誌器"""
    return logging.getLogger(name)