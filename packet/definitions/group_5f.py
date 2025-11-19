"""
5F 群組封包定義
"""

from config.constants import CONTROL_STRATEGY_MAP,FIELD_OPERATION_MAP,BEGIN_END_STATUS_MAP,PLAN_ID_MAP



# 5F 群組封包定義
F5_GROUP_DEFINITIONS = {

# =============時相資料庫管理=============    
    "5F03": {
        "name": "時相資料庫管理",
        "description": "主動回報號誌控制器步階轉換之資料",
        "reply_type": "主動回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0x03,
        "log_modes": ["receive"],
        
        # 统一字段列表，按順序定義，使用 index 表示位置
        "fields": [
            {"name": "時相編號", "index": 2, "type": "uint8"},          
            # 專門類型解析器
            {"name": "號誌位置圖", "index": 3, "type": "signal_map", "description": "號誌位置圖"},        
            {"name": "岔路數目", "index": 4, "type": "uint8"},
            {"name": "分相序號", "index": 5, "type": "uint8"},
            {"name": "步階序號", "index": 6, "type": "uint8"},
            {"name": "步階秒數", "index": 7, "type": "uint16", "endian": "big"},           
            # 專門類型解析器
            {"name": "燈號狀態列表", "index": 8, "type": "signal_status_list", "count_from": "岔路數目","description": "燈號狀態列表"}
        ],   
        "validation": {
            "type": "min_length",
            "value": 9,
            "error_message": "5F03資料長度不足"
        }
    },

    "5F13": {
        "name": "時相資料庫管理",
        "description": "設定號誌控制器時相排列",
        "reply_type": "設定",
        "needs_ack": True,
        "group": "5F",
        "command": 0x13,
        "log_modes": ["command"],
        
        "steps": [
            {
                "step": 1,
                "name": "基本參數",
                "description": "請輸入基本參數",
                "fields": ["時相編號", "號誌位置圖", "岔路數目", "綠燈分相數目"],
                "prompt": "步驟 1/3: 請輸入基本參數\n  時相編號(hex) + 號誌位置圖(binary) + 信號燈數量 + 綠燈分相數目\n  範例: 40 10101010 8 3\n> "
            },
            {
                "step": 2,
                "name": "燈號狀態列表",
                "description": "請輸入燈號狀態列表",
                "fields": ["燈號狀態列表"],
                "prompt": "步驟 2/3: 請輸入信號狀態列表 (共 {total} 個值，用空格分隔)\n  需要 {岔路數目} × {綠燈分相數目} = {total} 個狀態值\n  範例: 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85\n> "
            },
            {
                "step": 3,
                "name": "確認",
                "description": "確認並發送指令",
                "type": "confirmation",
                "preview": True,
                "prompt": "步驟 3/3: 確認發送？(y/n)\n{preview}\n> "
            }
        ],

        "fields": [
            {
                "name": "時相編號", # phase_order
                "index": 2,
                "type": "uint8",
                "description": "時相編號",
                "input_type": "hex"  
            },
            {
                "name": "號誌位置圖", # signal_map
                "index": 3,
                "type": "uint8",
                "description": "號誌位置圖",
                "input_type": "binary" # 高位在前二進制字符串
            },
            {
                "name": "岔路數目", # signal_count
                "index": 4,
                "type": "uint8",
                "description": "岔路數目"
            },
            {
                "name": "綠燈分相數目", # sub_phase_count
                "index": 5,
                "type": "uint8",
                "description": "綠燈分相數目"
            },
            {
                "name": "燈號狀態列表", # signal_status_list
                "index": 6,
                "type": "list",
                "item_type": "uint8",
                "count_from": lambda result: result.get("岔路數目", 0) * result.get("綠燈分相數目", 0),
                "description": "燈號狀態列表（每個分相包含 SignalCount 個狀態，共 SubPhaseCount 個分相）"
            }
        ],
        
        "format": "5F13 <時相編號(hex)> <號誌位置圖(binary)> <岔路數目> <綠燈分相數目> <燈號狀態列表>",
        "example": "5F13 40 10101010 8 3 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85 85",


        "validation": {
            "type": "min_length",
            "value": 6,
            "error_message": "5F13資料長度不足"
        }
    },

    "5F43": {
        "name": "時相資料庫管理",
        "description": "查詢號誌控制器之時相排列",
        "reply_type": "查詢",
        "needs_ack": True,
        "group": "5F",
        "command": 0x43,
        "log_modes": ["command"],
        
        "steps": [
            {
                "step": 1,
                "name": "參數輸入",
                "description": "請輸入時相編號",
                "fields": ["時相編號"],
                "prompt": "請輸入參數: <時相編號(hex)>\n  範例: 5F43 64\n> "
            }
        ],  

        "fields": [
            {
                "name": "時相編號",
                "index": 2,
                "type": "uint8",
                "description": "時相編號",
                "input_type": "hex"  
            }
        ],
        
        "format": "5F43 <時相編號>",
        "example": "5F43 64",
                
        "validation": {
            "type": "exact_length",
            "value": 3,
            "error_message": "5F43資料長度錯誤，應為 5F 43 + PhaseOrder"
        }
    },

    "5FC3": {
        "name": "時相資料庫管理",
        "description": "回報號誌控制器之時相排列",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0xC3,
        "log_modes": ["receive", "command"],
        
        "fields": [
            {"name": "時相編號", "index": 2, "type": "uint8"},
            # 專門類型解析器
            {"name": "號誌位置圖", "index": 3, "type": "signal_map", "description": "號誌位置圖"},
            {"name": "岔路數目", "index": 4, "type": "uint8"},
            {"name": "綠燈分相數目", "index": 5, "type": "uint8"},          
            # 專門類型解析器
            {
            "name": "燈號狀態列表", "index": 6, "type": "signal_status_list",  
            "count_from": lambda result: result.get("岔路數目", 0) * result.get("綠燈分相數目", 0),
            "description": "燈號狀態列表"
            }
        ],
        
        "validation": {
            "type": "min_length",
            "value": 6,
            "error_message": "5FC3資料長度不足"
        }
    },    

# =============目前控制策略管理=============    
    "5F40": {
        "name": "目前控制策略管理",
        "description": "查詢目前控制策略之設定內容",
        "reply_type": "查詢",
        "needs_ack": True,
        "group": "5F",
        "command": 0x40,
        "log_modes": ["command"], 

        "steps": [
            {
                "step": 1,
                "name": "確認",
                "description": "確認發送查詢指令",
                "type": "confirmation",
                "prompt": "確認發送 5F40 查詢指令？(y/n)\n> "
            }
        ],

        "fields": [],
        "format": "5F40",
        "example": "5F40",        

        "validation": {
            "type": "exact_length",
            "value": 2,
            "error_message": "5F40為查詢命令，無參數"
        }
    }, 

    "5F10": {
        "name": "目前控制策略管理",
        "description": "設定目前控制策略之內容",
        "reply_type": "設定",
        "needs_ack": True,
        "group": "5F",
        "command": 0x10,
        "log_modes": ["command"],
        
        "steps": [
            {
                "step": 1,
                "name": "參數輸入",
                "description": "請輸入控制策略參數",
                "fields": ["控制策略", "動態控制策略有效時間"]
            }
        ],
        
        "fields": [
            {
                "name": "控制策略",
                "index": 2,
                "type": "uint8",
                "description": "控制策略", # control_strategy
                "input_type": "binary"
            },
            {
                "name": "動態控制策略有效時間",
                "index": 3,
                "type": "uint8",
                "description": "動態控制策略有效時間（分鐘，0~255，0為不計時）", # effect_time
            }
        ],

        "format": "5F10 <控制策略(binary)> <動態控制策略有效時間(分鐘)>\n\n  控制策略為8位二進制(高位在前)：\n    bit 0: 定時控制 (0x01)\n    bit 1: 動態控制 (0x02)\n    bit 2: 路口手動 (0x04)\n    bit 3: 中央手動 (0x08)\n    bit 4: 時相控制 (0x10)\n    bit 5: 即時控制 (0x20)\n    bit 6: 觸動控制 (0x40)\n    bit 7: 特別路線控制 (0x80)>\n",
        "example": "5F10 00000011 60 (啟用定時控制+動態控制)", # 00000011 = 二進位 

        "validation": {
            "type": "exact_length",
            "value": 4,
            "error_message": "5F10資料長度錯誤，應為 5F 10 + ControlStrategy + EffectTime"
        }
    },
    
    "5FC0": {
        "name": "目前控制策略管理",
        "description": "回報目前控制策略之內容",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0xC0,
        "log_modes": ["receive", "command"],
        "fields": [
            # control_strategy
            {"name": "控制策略", "index": 2, "type": "uint8", "mapping": CONTROL_STRATEGY_MAP},
            # effect_time
            {"name": "動態控制策略有效時間", "index": 3, "type": "uint8"}
        ],
        "validation": {
            "type": "exact_length",
            "value": 4,
            "error_message": "5FC0資料長度錯誤，應為 5F C0 + ControlStrategy + EffectTime"
        }
    },

    "5F00": {
        "name": "目前控制策略管理",
        "description": "自動回報控制策略之目前執行內容",
        "reply_type": "主動回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0x00,
        "log_modes": ["receive", "command"],
        
        "fields": [
            # control_strategy
            {"name": "控制策略", "index": 2, "type": "uint8", "mapping": CONTROL_STRATEGY_MAP},
            # begin_end_status
            {"name": "控制策略狀態", "index": 3, "type": "uint8", "mapping": BEGIN_END_STATUS_MAP},
        ],
        
        "validation": {
            "type": "exact_length",
            "value": 4,
            "error_message": "5F00資料長度錯誤，應為 5F 00 + ControlStrategy + BeginEnd"
        }
    },
# =============時制計畫基本參數管理=============
    "5F14": {
        "name": "時制計畫基本參數管理",
        "description": "設定路口時制計畫之基本參數",
        "reply_type": "設定",
        "needs_ack": True,
        "group": "5F",
        "command": 0x14,
        "log_modes": ["command"],
        
        "steps": [
            {
                "step": 1,
                "name": "基本參數",
                "description": "請輸入基本參數",
                "fields": ["時制計畫編號", "綠燈分相數目"],
                "prompt": "步驟 1/3: 請輸入基本參數\n  時制計畫編號(1~40) + 綠燈分相數目(1~8)\n  範例: 1 3\n> "
            },
            {
                "step": 2,
                "name": "分相基本參數列表",
                "description": "請輸入每個分相的基本參數",
                "fields": ["分相基本參數列表"],
                "prompt": "步驟 2/3: 請輸入分相基本參數列表 (共 {total} 個值，用空格分隔)\n  每個分相需要 6 個參數：\n    1. 最短綠燈秒數 (0~255)\n    2. 最長綠燈秒數 (0~8190，系統會自動轉換為2字節)\n    3. 黃燈秒數 (0~9)\n    4. 全紅秒數 (0~9)\n    5. 行人綠閃秒數 (0~99)\n    6. 行人紅燈秒數 (0~99)\n  需要 {綠燈分相數目} 個分相 × 6 個參數 = {total} 個值\n  範例: 10 60 3 2 5 10 15 90 4 3 6 12 20 120 5 4 7 15\n> "
            },
            {
                "step": 3,
                "name": "確認",
                "description": "確認並發送指令",
                "type": "confirmation",
                "preview": True,
                "prompt": "步驟 3/3: 確認發送？(y/n)\n{preview}\n> "
            }
        ],
        
        "fields": [
            {
                "name": "時制計畫編號", # plan_id
                "index": 2,
                "type": "uint8",
                "description": "時制計畫編號 (0~48)",
                "mapping": PLAN_ID_MAP
            },
            {
                "name": "綠燈分相數目", # sub_phase_count
                "index": 3,
                "type": "uint8",
                "description": "綠燈分相數目 (1~8)"
            },
            {
                "name": "分相基本參數列表", # sub_phase_param_list
                "index": 4,
                "type": "list",
                "item_type": "uint8",
                "count_from": lambda result: result.get("綠燈分相數目", 0) * 7,  # 每个分相实际需要 7 个字节
                "description": "分相基本參數列表（每個分相：MinGreen(1) + MaxGreen(2) + Yellow(1) + AllRed(1) + PedGreenFlash(1) + PedRed(1)）"
            }
        ],
        
        "format": "5F14 <時制計畫編號(1~40)> <綠燈分相數目(1~8)> <分相基本參數列表...>",
        "example": "5F14 1 3 10 60 3 2 5 10 15 90 4 3 6 12 20 120 5 4 7 15",
        
        "validation": {
            "type": "min_length",
            "value": 4,
            "error_message": "5F14資料長度不足"
        }
    },  

    "5F44": {
        "name": "時制計畫基本參數管理",
        "description": "查詢路口時制計畫的基本參數",
        "reply_type": "查詢",
        "needs_ack": True,
        "group": "5F",
        "command": 0x44,
        "log_modes": ["command"],
        
        "steps": [
            {
                "step": 1,
                "name": "參數輸入",
                "description": "請輸入時制計畫編號",
                "fields": ["時制計畫編號"],
                "prompt": "請輸入參數: <時制計畫編號(1~40)>\n  範例: 5F44 1 (查詢定時時制 PlanID: 1 的基本參數)\n> "
            }
        ],
        
        "fields": [
            {
                "name": "時制計畫編號",
                "index": 2,
                "type": "uint8",
                "description": "時制計畫編號 (1~40)",
                "mapping": PLAN_ID_MAP
            }
        ],
        
        "format": "5F44 <時制計畫編號(1~40)>",
        "example": "5F44 1",
        
        "validation": {
            "type": "exact_length",
            "value": 3,
            "error_message": "5F44資料長度錯誤，應為 5F 44 + PlanID"
        }
    },  

# =============設定執行時制計畫=============  
    "5F18": {
        "name": "設定執行時制計畫",
        "description": "選擇執行之時制計畫",
        "reply_type": "設定",
        "needs_ack": True,
        "group": "5F",
        "command": 0x18,
        "log_modes": ["command"],
        
        "steps": [
            {
                "step": 1,
                "name": "參數輸入",
                "description": "請輸入時制計畫編號",
                "fields": ["時制計畫編號"],
                "prompt": "請輸入參數: <時制計畫編號(1~40)>\n  範例: 5F18 1 (選擇定時時制 PlanID: 1)\n> "
            }
        ],
        
        "fields": [
            {
                "name": "時制計畫編號", # plan_id
                "index": 2,
                "type": "uint8",
                "description": "時制計畫編號 (1~40)",
                "mapping": PLAN_ID_MAP
            }
        ],
        
        "format": "5F18 <時制計畫編號(1~40)>",
        "example": "5F18 1",
        
        "validation": {
            "type": "exact_length",
            "value": 3,
            "error_message": "5F18資料長度錯誤，應為 5F 18 + PlanID"
        }
    },
# =============現場操作回報=============    
    "5F08": {
        "name": "現場操作回報",
        "description": "回報號誌控制器現場操作",
        "reply_type": "主動回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0x08,
        "log_modes": ["receive"],
        "fields": [
            # field_operation
            {"name": "現場操作碼", "index": 2, "type": "uint8", "mapping": FIELD_OPERATION_MAP}
        ],
        
        "validation": {
            "type": "exact_length",
            "value": 3,
            "error_message": "5F08資料長度錯誤"
        }
    },

# =============目前時制計畫管理=============    
    "5F48": {
        "name": "目前時制計畫管理",
        "description": "查詢目前時制計畫內容",
        "reply_type": "查詢",
        "needs_ack": True,
        "group": "5F",
        "command": 0x48,
        "log_modes": ["command"],
        
        "steps": [
            {
                "step": 1,
                "name": "確認",
                "description": "確認發送查詢指令",
                "type": "confirmation",
                "prompt": "確認發送 5F48 查詢指令？(y/n)\n> "
            }
        ],

        "fields": [],
        "format": "5F48",
        "example": "5F48",

        "validation": {
            "type": "exact_length",
            "value": 2,
            "error_message": "5F48為查詢命令，無參數"
        }
    },

    "5FC8": {
        "name": "時制計畫回報",
        "description": "回報目前時制計畫內容",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0xC8,
        "log_modes": ["receive", "command"],
        "fields": [
            # plan_id
            {"name": "時制計畫編號", "index": 2, "type": "uint8"},
            # direct
            {"name": "基準方向", "index": 3, "type": "uint8"},
            # phase_order
            {"name": "時相編號", "index": 4, "type": "uint8"},
            # sub_phase_count
            {"name": "綠燈分相數", "index": 5, "type": "uint8"},
            # green_times
            {"name": "各分相綠燈時間", "index": 6, "type": "list", "item_type": "uint16", "endian": "big", "count_from": "綠燈分相數"},
            # cycle_time
            {"name": "週期秒數", "index": None, "type": "uint16", "endian": "big"},
            # offset
            {"name": "時差秒數", "index": None, "type": "uint16", "endian": "big"}
        ],
        
        "validation": {
            "type": "min_length",
            "value": 7,
            "error_message": "5FC8資料長度不足"
        }
    },

# =============一般日時段型態管理=============    
    "5F46": {
        "name": "一般日時段型態查詢",
        "description": "查詢一般日時段型態之設定內容",
        "reply_type": "查詢",
        "needs_ack": True,
        "group": "5F",
        "command": 0x46,
        "log_modes": ["command"],
        
        "steps": [
            {
                "step": 1,
                "name": "參數輸入",
                "description": "請輸入時段類型和查詢參數",
                "fields": ["時段類型", "查詢參數"],
                "prompt": "步驟 1/1: 請輸入參數\n  格式1: <時段類型> FF (例如: 01 FF) - 查詢一般日時段\n  格式2: FF <星期> (例如: FF 1) - 查詢星期\n  時段類型: 1~7 (一般日)\n  星期: 1~7 (週一到週日), 11~17 (隔週休)\n> "
            }
        ],
        
        "fields": [
            {
                "name": "時段類型",
                "index": 2,
                "type": "uint8",
                "input_type": "hex",
                "description": "時段類型 (1~7: 一般日, 0xFF: 查詢星期)"
            },
            {
                "name": "查詢參數",
                "index": 3,
                "type": "uint8",
                "input_type": "hex",
                "description": "查詢參數 (0xFF: 一般日時段, 1~7/11~17: 星期)"
            }
        ],
        
        "format": "5F46 <時段類型> <查詢參數>",
        "example": "5F46 01 FF 或 5F46 FF 1",
        
        "validation": {
            "type": "min_length",
            "value": 3,
            "error_message": "5F46資料長度不足"
        }
    },

    "5FC6": {
        "name": "一般日時段型態查詢回報", 
        "description": "週內日時段切分內容",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0xC6,
        "log_modes": ["receive","command"],
        "fields": [
            # segment_type
            {"name": "時段類型", "index": 2, "type": "uint8"},
            # segment_count
            {"name": "時段數量", "index": 3, "type": "uint8"},
            
            # time_segment_list
            # 專門類型解析器 
            {"name": "時段列表", "index": 4, "type": "time_segment_list", "count_from": "時段數量"},
            
            # num_weekday
            {"name": "星期數量", "index": None, "type": "uint8"},
            
            # weekday(num_weekday)
            # 專門類型解析器
            {"name": "星期列表", "index": None, "type": "weekday_list", "count_from": "星期數量"},
        ],
        
        "validation": {
            "type": "min_length",
            "value": 5,
            "error_message": "5FC6資料長度不足"
        }
    },

# =============時相步階變換控制管理=============    
    "5F0C": {
        "name": "時相步階變換控制管理",
        "description": "主動回報號誌控制器現行時相及步階",
        "reply_type": "主動回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0x0C,
        "log_modes": ["receive"],
        "fields": [
            # control_strategy
            {"name": "控制策略", "index": 2, "type": "uint8", "mapping": CONTROL_STRATEGY_MAP},
            # sub_phase_id
            {"name": "分相序號", "index": 3, "type": "uint8"},
            # step_id
            {"name": "步階序號", "index": 4, "type": "uint8"}
        ],
        "validation": {
            "type": "exact_length",
            "value": 5,
            "error_message": "5F0C資料長度錯誤，應為 5F 0C + ControlStrategy + SubPhaseID + StepID"
        }
    },
}

