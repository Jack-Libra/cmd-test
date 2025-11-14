"""
命令元数据定义
集中管理所有命令的格式、参数、示例等信息
"""

# 命令元数据定义
COMMAND_METADATA = {
    "5F40": {
        "handler": "_execute_5f40_command",
        "description": "查詢控制策略",
        "format": "5F40",
        "example": "5F40",
        "params": [],
        "category": "查詢"
    },
    "5F10": {
        "handler": "_execute_5f10_command",
        "description": "設定控制策略",
        "format": "5F10 <controlStrategy> <effectTime>",
        "example": "5F10 1 60",
        "params": [
            {"name": "controlStrategy", "type": "int", "range": (0, 255), "description": "控制策略值"},
            {"name": "effectTime", "type": "int", "range": (0, 255), "description": "有效時間（分鐘）"}
        ],
        "category": "設定"
    },
    "5F48": {
        "handler": "_execute_5f48_command",
        "description": "查詢時制計畫",
        "format": "5F48",
        "example": "5F48",
        "params": [],
        "category": "查詢"
    },
    "5F18": {
        "handler": "_execute_5f18_command",
        "description": "選擇時制計畫",
        "format": "5F18 <planId>",
        "example": "5F18 1",
        "params": [
            {"name": "planId", "type": "int", "range": (0, 255), "description": "時制計畫編號"}
        ],
        "category": "設定"
    },
    "5F43": {
        "handler": "_execute_5f43_command",
        "description": "查詢時相排列",
        "format": "5F43 <phaseOrder>",
        "example": "5F43 40",
        "params": [
            {"name": "phaseOrder", "type": "hex", "range": (0, 0xFE), "description": "時相編號 (0x00~0xFE)"}
        ],
        "category": "查詢"
    },
    "5F13": {
        "handler": "_execute_5f13_command",
        "description": "設定時相排列",
        "format": "5F13 <phaseOrder> <signalMap> <signalCount> <subPhaseCount> <signalStatus...>",
        "example": "5F13 40 D5 5 5 81 44 81 41 81 ...",
        "params": [
            {"name": "phaseOrder", "type": "hex", "range": (0, 0xFE), "description": "時相編號"},
            {"name": "signalMap", "type": "hex", "range": (0, 0xFF), "description": "號誌位置圖"},
            {"name": "signalCount", "type": "int", "range": (1, 8), "description": "信號燈數量"},
            {"name": "subPhaseCount", "type": "int", "range": (1, 8), "description": "綠燈分相數目"},
            {"name": "signalStatus", "type": "list", "count_from": "signalCount * subPhaseCount", "description": "信號狀態列表"}
        ],
        "category": "設定"
    }
}

# 從元數據自動生成處理器映射
COMMAND_HANDLERS = {
    cmd: meta["handler"] 
    for cmd, meta in COMMAND_METADATA.items()
}

# 按類別分組命令
COMMANDS_BY_CATEGORY = {
    "查詢": [cmd for cmd, meta in COMMAND_METADATA.items() if meta.get("category") == "查詢"],
    "設定": [cmd for cmd, meta in COMMAND_METADATA.items() if meta.get("category") == "設定"],
}
