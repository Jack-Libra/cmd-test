# 控制器清單
TRAFFIC_CONTROLLERS = {
    "TC003": {
        "TC_ip": "192.168.13.89",
        "TC_port": 7002,
        "BackServer_ip": "0.0.0.0",
        "BackServer_port": 8889,
        "TransServer_ip": "0.0.0.0",
        "TransServer_port": 5555,
    }
}


# 日誌設定
LOG_DIR = "./logs"
DATA_DIR = "./data"

# 通訊設定
TIMEOUT = 5.0  # 秒
RETRY_COUNT = 3