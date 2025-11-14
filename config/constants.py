"""
協議常量定義
"""

# 封包控制字符
DLE = 0xAA
STX = 0xBB
ETX = 0xCC
ACK = 0xDD
NAK = 0xEE


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

# 控制策略配置
CONTROL_STRATEGY_CONFIG = [
    ("fixed_time", 0x01, "定時控制"),
    ("dynamic", 0x02, "動態控制"),
    ("intersection_manual", 0x04, "路口手動"),
    ("central_manual", 0x08, "中央手動"),
    ("phase_control", 0x10, "時相控制"),
    ("immediate_control", 0x20, "即時控制"),
    ("actuated", 0x40, "觸動控制"),
    ("special_route", 0x80, "特別路線控制"),
]

def process_control_strategy(control_strategy):
    """處理控制策略位（通用函數）"""
    return {
        key: bool(control_strategy & bit)
        for key, bit, _ in CONTROL_STRATEGY_CONFIG
    }

def format_control_strategy_desc(strategy_details):
    """
    格式化控制策略描述字符串
    
    Args:
        strategy_details: 策略詳情字典，包含各個策略位的布爾值
    
    Returns:
        格式化後的描述字符串，如 "定時控制、動態控制" 或 "無設定策略"
    """
    result = []
    for key, _, description in CONTROL_STRATEGY_CONFIG:
        if strategy_details.get(key, False):
            result.append(description)
    
    return "、".join(result) if result else "無設定策略"

# 硬件狀態位映射（0F04）
HARDWARE_STATUS_MAP = [
    (0, "CPU模組錯誤"),
    (1, "記憶體錯誤"),
    (2, "計時器錯誤"),
    (3, "看門狗計時器錯誤"),
    (4, "電源錯誤（AC 80V~130V 之外）"),
    (5, "I/O單元錯誤（DI/O故障：行人觸動、子機連鎖）"),
    (6, "信號驅動單元錯誤"),
    (7, "信號頭錯誤"),
    (8, "通訊連接"),
    (9, "機櫃開啟"),
    (10, "時制計畫錯誤"),
    (11, "信號衝突錯誤"),
    (12, "信號電源錯誤"),
    (13, "時制計畫轉換中"),
    (14, "控制器就緒"),
    (15, "通訊線路不良（框架錯誤）")
]

# 錯誤碼配置(0F81)
# (錯誤鍵, 位值, 描述, 參數格式函數)
ERROR_CODE_CONFIG = [
    ("invalid_msg", 0x01, "無此訊息", None),
    ("no_response", 0x02, "無法回應資料", None),
    ("param_invalid", 0x04, "參數值無效", lambda p: f"位置:{p}"),
    ("no_param", 0x08, "位元組總參數數目錯誤", lambda p: f"錯誤值:{p}"),
    ("prep_error", 0x10, "設備類別錯誤", None),
    ("timeout", 0x20, "逾時", None),
    ("exceed_limit", 0x40, "參數值超過硬體限制", lambda p: f"位置:{p}"),
    ("reported", 0x80, "已被訊息等級設定排除", None),
]

# 現場操作碼映射(5F08)
FIELD_OPERATION_MAP = {
    0x01: "現場手動",
    0x02: "現場全紅",
    0x40: "現場閃光",
    0x80: "上次現場操作回復"
}


# 控制策略狀態映射(5F00)
BEGIN_END_STATUS_MAP = {
    0x00: "結束",
    0x01: "啟動",
    0x02: "路口手動要求",
    0x03: "路口手動超時回報"
}