"""
協議常量定義
"""

# 幀控制字符
DLE = 0xAA
STX = 0xBB
ETX = 0xCC
ACK = 0xDD
NAK = 0xEE

# 控制策略位元定義
CS_FIXED_TIME = 0x01
CS_DYNAMIC = 0x02
CS_INTERSECTION_MANUAL = 0x04
CS_CENTRAL_MANUAL = 0x08
CS_PHASE_CONTROL = 0x10
CS_IMMEDIATE_CONTROL = 0x20
CS_ACTUATED = 0x40
CS_SPECIAL_ROUTE = 0x80

# 設備配置
DEVICE_CONFIG = {
    3: {
        "TC_ip": "192.168.13.89",
        "TC_port": 7002,
        "BackServer_ip": "0.0.0.0",
        "BackServer_port": 8889,
        "TransServer_ip": "0.0.0.0",
        "TransServer_port": 5555,
    }
}

