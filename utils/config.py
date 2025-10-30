# 控制器清單
TRAFFIC_CONTROLLERS = {
    "TC003": {
        "id": "TC003",
        "ip": "192.168.13.89",
        "port": 7002
    }
}

# 本機監聽設定（接收控制器回報）
LISTEN_HOST = "192.168.13.89"
LISTEN_PORT = 7002

# 日誌設定
LOG_DIR = "./logs"
DATA_DIR = "./data"

# 通訊設定
TIMEOUT = 5.0  # 秒
RETRY_COUNT = 3