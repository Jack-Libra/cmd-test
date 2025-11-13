# logging/setup.py
"""
日誌配置
"""

import logging
import os
from pathlib import Path
_logging_configured = {} 

def setup_logging(log_dir: str = "logs", log_file: str = "traffic_control.log", mode: str = "default"):
    """設置日志系統
    
    Args:
        log_dir: 日誌目錄
        log_file: 日誌文件名
        mode: 模式名稱（用於區分不同的logger實例）
    """
    # 創建日誌目錄
    Path(log_dir).mkdir(exist_ok=True)
    
    # 為每個模式創建獨立的logger
    logger_name = f"tc.{mode}"
    logger = logging.getLogger(logger_name)
    
    # 如果已經配置過，直接返回
    if logger_name in _logging_configured and logger.handlers:
        return logger
    
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
    
    # 配置logger
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False  # 防止日誌向上傳播
    
    _logging_configured[logger_name] = True
    
    return logger

def get_logger(name: str = "tc"):
    """獲取日誌器"""
    return logging.getLogger(name)