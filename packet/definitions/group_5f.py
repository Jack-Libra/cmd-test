"""
5F 群組封包定義
"""

from utils import int_to_binary_list
from config.constants import process_control_strategy,FIELD_OPERATION_MAP,BEGIN_END_STATUS_MAP


def format_5f03_signal_status(signal_status_list, result=None):
    """
    直接將信號狀態列表格式化為字符串列表（一步完成處理和格式化）
    
    Args:
        signal_status_list: 原始信號狀態字節列表
    
    Returns:
        格式化後的字符串列表，格式：["   方向 1: 全紅、行人紅燈", ...]
    """
    formatted_statuses = []
    
    for i, status_byte in enumerate(signal_status_list, 1):
        status_list = int_to_binary_list(status_byte)
        
        # 提取行人燈位
        pedgreen_bit = status_list[6] if len(status_list) > 6 else 0
        pedred_bit = status_list[7] if len(status_list) > 7 else 0
        
        # 判斷行人燈狀態（特殊邏輯：兩個位都為1表示閃爍）
        if pedgreen_bit and pedred_bit:
            ped_status = "行人綠燈閃爍"
        elif pedgreen_bit:
            ped_status = "行人綠燈"
        elif pedred_bit:
            ped_status = "行人紅燈"
        else:
            ped_status = None
        
        # 構建狀態描述
        status_parts = []
        
        # 車道燈狀態（互斥：全紅、黃燈、綠燈）
        if len(status_list) > 0 and status_list[0]:
            status_parts.append("全紅")
        elif len(status_list) > 1 and status_list[1]:
            status_parts.append("黃燈")
        elif len(status_list) > 2 and status_list[2]:
            status_parts.append("綠燈")
        
        # 轉向燈狀態（可組合：左轉、直行、右轉）
        turn_parts = []
        if len(status_list) > 3 and status_list[3]:
            turn_parts.append("左轉")
        if len(status_list) > 4 and status_list[4]:
            turn_parts.append("直行")
        if len(status_list) > 5 and status_list[5]:
            turn_parts.append("右轉")
        if turn_parts:
            status_parts.append("、".join(turn_parts))
        
        # 行人燈狀態
        if ped_status:
            status_parts.append(ped_status)
        
        # 組合最終描述
        status_desc = "、".join(status_parts) if status_parts else "未知"
        formatted_statuses.append(f"   方向 {i}: {status_desc}")
    
    return formatted_statuses



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
            {"name": "phase_order", "index": 2, "type": "uint8", "description": "時相編號"},
            
            # signal_map 直接轉換為列表，不顯示原始值
            {
                "name": "號誌位置圖",
                "index": 3,
                "type": "uint8",
                "description": "號誌位置圖",
                "input_type": "binary",
                "post_process": lambda value, result: f"0x{value:02X} = {int_to_binary_list(value)}"
                # 結果：signal_map = [1, 0, 1, 0, 1, 0, 1, 0] 而不是 85
            },
            
            {"name": "signal_count", "index": 4, "type": "uint8", "description": "信號燈數量"},
            {"name": "sub_phase_id", "index": 5, "type": "uint8", "description": "分相序號"},
            {"name": "step_id", "index": 6, "type": "uint8", "description": "步階序號"},
            {"name": "step_sec", "index": 7, "type": "uint16", "endian": "big", "description": "步階秒數"},
            
            # 信號狀態列表：直接格式化為字符串列表
            {
                "name": "信號狀態列表",
                "index": 8,
                "type": "list",
                "item_type": "uint8",
                "count_from": "signal_count",
                "description": "信號狀態列表",
                "post_process": format_5f03_signal_status
                
            }
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
        #"interaction_type": "multi_step",
        #"steps": 3,

        "fields": [
            {
                "name": "phase_order",
                "index": 2,
                "type": "uint8",
                "description": "時相編號",
                "input_type": "hex"  
            },
            {
                "name": "號誌位置圖",
                "index": 3,
                "type": "uint8",
                "description": "號誌位置圖",
                "input_type": "binary" # 低位在前二進制字符串
            },
            {
                "name": "signal_count",
                "index": 4,
                "type": "uint8",
                "description": "信號燈數量"
            },
            {
                "name": "sub_phase_count",
                "index": 5,
                "type": "uint8",
                "description": "綠燈分相數目"
            },
            {
                "name": "信號狀態列表",
                "index": 6,
                "type": "list",
                "item_type": "uint8",
                "count_from": lambda result: result.get("signal_count", 0) * result.get("sub_phase_count", 0),
                "description": "信號狀態列表（每個分相包含 SignalCount 個狀態，共 SubPhaseCount 個分相）"
            }
        ],
        
        "format": "5F13 <phase_order> <號誌位置圖> <signal_count> <sub_phase_count> <信號狀態列表...>",
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
        
        "fields": [
            {
                "name": "phase_order",
                "index": 2,
                "type": "uint8",
                "description": "時相編號",
                "input_type": "hex"  
            }
        ],
        
        "format": "5F43 <phase_order>",
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
            {"name": "phase_order", "index": 2, "type": "uint8", "description": "時相編號"},
            {
                "name": "號誌位置圖",
                "index": 3,
                "type": "uint8",
                "description": "號誌位置圖",
                "post_process": lambda value, result: f"0x{value:02X} = {int_to_binary_list(value)}"
            },
            {"name": "signal_count", "index": 4, "type": "uint8", "description": "信號燈數量"},
            {"name": "sub_phase_count", "index": 5, "type": "uint8", "description": "綠燈分相數目"},
            {
                "name": "信號狀態列表",
                "index": 6,
                "type": "list",
                "item_type": "uint8",
                "count_from": lambda result: result.get("signal_count", 0) * result.get("sub_phase_count", 0),
                "description": "信號狀態列表（每個分相包含 SignalCount 個狀態，共 SubPhaseCount 個分相）",
                "post_process": format_5f03_signal_status
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
        "fields": [
            {
                "name": "control_strategy",
                "index": 2,
                "type": "uint8",
                "description": "控制策略",
                "input_type": "hex"
            },
            {
                "name": "effect_time",
                "index": 3,
                "type": "uint8",
                "description": "動態控制策略有效時間（分鐘，0~255，0為不計時）"
            }
        ],

        "format": "5F10 <control_strategy> <effect_time>",
        "example": "5F10 03 60", # 3 = 16進位 0x03

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
            {
                "name": "control_strategy",
                "index": 2,
                "type": "uint8",
                "description": "控制策略",
                "post_process": lambda value, result: {
                    "raw": value,
                    **process_control_strategy(value)
                }
            },
            {
                "name": "effect_time",
                "index": 3,
                "type": "uint8",
                "description": "動態控制策略有效時間（分鐘，0~255，0為不計時）"
            }
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
        "log_modes": ["receive"],
        
        "fields": [
            {
                "name": "control_strategy",
                "index": 2,
                "type": "uint8",
                "description": "控制策略（只回報目前執行之控制策略的對應位元資料）",
                "post_process": lambda value, result: {
                    "raw": value,
                    **process_control_strategy(value)
                }
            },
            {
                "name": "begin_end",
                "index": 3,
                "type": "uint8",
                "description": "控制策略狀態",
                "mapping": BEGIN_END_STATUS_MAP
            }
        ],
        
        "validation": {
            "type": "exact_length",
            "value": 4,
            "error_message": "5F00資料長度錯誤，應為 5F 00 + ControlStrategy + BeginEnd"
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
            {
                "name": "現場操作碼",
                "index": 2,  # PAYLOAD[0]
                "type": "uint8",
                "description": "現場操作碼",             
                "mapping": FIELD_OPERATION_MAP,
                # 後處理：格式化輸出
                #"post_process": lambda value, result: f"0x{value:02X}H ({result.get('_mapping_desc', '未知')})"
            }
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
            {
                "name": "時制計畫編號",
                "index": 2,
                "type": "uint8",
                "description": "時制計畫編號"
            },
            {
                "name": "基準方向",
                "index": 3,
                "type": "uint8",
                "description": "基準方向"
            },
            {
                "name": "時相種類編號",
                "index": 4,
                "type": "uint8",
                "description": "時相種類編號"
            },
            {
                "name": "綠燈分相數",
                "index": 5,
                "type": "uint8",
                "description": "綠燈分相數"
            },
            {
                "name": "各分相綠燈時間",
                "index": 6,
                "type": "list",
                "item_type": "uint16", 
                "endian": "big",  # 添加：指定字節序
                "count_from": "綠燈分相數", 
                "description": "各分相綠燈時間（秒數，0~8190）"
            },
            {
                "name": "週期秒數",
                "index": None,  # 使用 current_index（自動跟蹤）
                "type": "uint16",
                "endian": "big",
                "description": "週期秒數"
            },
            {
                "name": "時差秒數",
                "index": None,  # 使用 current_index（自動跟蹤）
                "type": "uint16",
                "endian": "big",
                "description": "時差秒數"
            }
        ],
        
        "validation": {
            "type": "min_length",
            "value": 7,
            "error_message": "5FC8資料長度不足"
        }
    },

# =============一般日時段型態管理=============    
    "5FC6": {
        "name": "一般日時段型態查詢回報",
        "description": "週內日時段切分內容",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0xC6,
        "log_modes": ["receive","command"],
        "fields": [
            {
                "name": "時段類型",
                "index": 2,
                "type": "uint8",
                "description": "時段類型"
            },
            {
                "name": "時段數量",
                "index": 3,
                "type": "uint8",
                "description": "時段數量"
            },
            {
                "name": "時段列表", #(Hour+Min+PlanID)(segment_count)
                "index": 4,  # PAYLOAD[2] 開始
                "type": "struct_list",
                "item_fields": [
                    {"name": "hour", "type": "uint8"},
                    {"name": "minute", "type": "uint8"},
                    {"name": "plan_id", "type": "uint8"}
                ],
                "count_from": "時段數量",
                "description": "時段列表"
            },
            {
                "name": "星期數量",
                "index": None, # 使用 current_index（自動跟蹤）
                "type": "uint8",
                "description": "星期數量"
            },
            {
                "name": "星期列表",
                "index": None, # 使用 current_index（自動跟蹤）
                "type": "list",
                "item_type": "uint8",
                "count_from": "星期數量",
                "index_calc": lambda result: 4 + result.get("時段數量", 0) * 3 + 1,
                "description": "星期列表"
            }
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
            {
                "name": "control_strategy",
                "index": 2,
                "type": "uint8",
                "description": "控制策略",
                "post_process": lambda value, result: {
                    "raw": value,
                    **process_control_strategy(value)
                }
            },
            {
                "name": "sub_phase_id",
                "index": 3,
                "type": "uint8",
                "description": "分相序號"
            },
            {
                "name": "step_id",
                "index": 4,
                "type": "uint8",
                "description": "步階序號"
            }
        ],
        "validation": {
            "type": "exact_length",
            "value": 5,
            "error_message": "5F0C資料長度錯誤，應為 5F 0C + ControlStrategy + SubPhaseID + StepID"
        }
    },
}

