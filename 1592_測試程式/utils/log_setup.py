import logging
import sys
import os

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_FILE = os.path.join(LOG_DIR, 'traffic_control.log')

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler], format=LOG_FORMAT)
logger = logging.getLogger("tc")

# 日誌函數
def log_info(message):
    logger.info(message)

def log_warning(message):
    logger.warning(message)

def log_error(message):
    logger.error(message)

def log_packet_received(packet_type, tc_id, details=""):
    if details:
        log_info(f"收到 {packet_type} 封包 (TC{tc_id:03d}): {details}")
    else:
        log_info(f"收到 {packet_type} 封包 (TC{tc_id:03d})")

def log_packet_sent(packet_type, tc_id, target_ip, target_port, details=""):
    if details:
        log_info(f"發送 {packet_type} 封包到 {target_ip}:{target_port} (TC{tc_id:03d}): {details}")
    else:
        log_info(f"發送 {packet_type} 封包到 {target_ip}:{target_port} (TC{tc_id:03d})")