"""
協議常量定義
"""

#============================== 封包控制字符 ==============================
DLE = 0xAA
STX = 0xBB
ETX = 0xCC
ACK = 0xDD
NAK = 0xEE

#============================== 設備配置 ==============================
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

#============================== 控制策略配置 ==============================
CONTROL_STRATEGY_CONFIG = [
    (0x01, "定時控制"),
    (0x02, "動態控制"),
    (0x04, "路口手動"),
    (0x08, "中央手動"),
    (0x10, "時相控制"),
    (0x20, "即時控制"),
    (0x40, "觸動控制"),
    (0x80, "特別路線控制"),
]

def CONTROL_STRATEGY_MAP(value):
    """
    控制策略映射函数（用于 mapping 字段）
    直接返回格式化字符串，如 "定時控制、動態控制 (0x03)"
    """
    result = []
    for bit, description in CONTROL_STRATEGY_CONFIG:
        if value & bit:
            result.append(description)
    
    strategy_desc = "、".join(result) if result else "無設定策略"
    return f"{strategy_desc} (0x{value:02X})"

#============================== 硬件狀態位映射（0F04） ==============================
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

#============================== 錯誤碼配置(0F81) ==============================
# (位值, 描述)
ERROR_CODE_CONFIG = [
    (0x01, "無此訊息"),
    (0x02, "無法回應資料"),
    (0x04, "參數值無效"),
    (0x08, "位元組總參數數目錯誤"),
    (0x10, "設備類別錯誤"),
    (0x20, "逾時"),
    (0x40, "參數值超過硬體限制"),
    (0x80, "已被訊息等級設定排除"),
]

PARAM_LABELS = {0x04: "位置", 0x08: "錯誤值", 0x40: "位置"}

def ERROR_CODE_MAP(value):
    """
    錯誤碼映射函数（用于 mapping 字段）
    返回格式化字符串，使用占位符 {xx} 表示需要參數的位置
    """
    errors = [
        f"{desc}({PARAM_LABELS[bit]}:{{xx}})" if bit in PARAM_LABELS else desc
        for bit, desc in ERROR_CODE_CONFIG
        if value & bit
    ]
    return f"{'、'.join(errors)} (0x{value:02X})" if errors else f"未知錯誤 (0x{value:02X})"

#============================== 現場操作碼映射(5F08) ==============================
FIELD_OPERATION_MAP = {
    0x01: "現場手動",
    0x02: "現場全紅",
    0x40: "現場閃光",
    0x80: "上次現場操作回復"
}


#============================== 控制策略狀態映射(5F00) ==============================
BEGIN_END_STATUS_MAP = {
    0x00: "結束",
    0x01: "啟動",
    0x02: "路口手動要求",
    0x03: "路口手動超時回報"
}

#============================== 時制計畫編號映射 ==============================
def PLAN_ID_MAP(value):
    """
    時制計畫編號映射函数（用于 mapping 字段）
    根據 PlanID 返回對應的時制計畫類型
    """
    if value == 0:
        return "動態時制(直接執行)"
    elif 1 <= value <= 40:
        return f"定時時制 (PlanID: {value})"
    elif value == 47:
        return "鐵路時制"
    elif value == 48:
        return "基本時制(預設時制,故障時制)"
    else:
        return f"未知時制計畫 (PlanID: {value})"
    