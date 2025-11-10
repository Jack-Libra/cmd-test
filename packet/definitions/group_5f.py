"""
5F 群組封包定義
"""

from core.utils import int_to_binary_list
from config.constants import (
    CS_FIXED_TIME, CS_DYNAMIC, CS_INTERSECTION_MANUAL, CS_CENTRAL_MANUAL,
    CS_PHASE_CONTROL, CS_IMMEDIATE_CONTROL, CS_ACTUATED, CS_SPECIAL_ROUTE
)

def process_5f03_signal_status(signal_status_list):
    """處理5F03信號狀態（行人燈邏輯）"""
    signal_status_details = []
    
    for status in signal_status_list:
        status_list = int_to_binary_list(status)
        
        # 提取原始位
        pedgreen_bit = status_list[6] if len(status_list) > 6 else 0
        pedred_bit = status_list[7] if len(status_list) > 7 else 0
        
        # 判斷行人燈狀態邏輯
        if pedgreen_bit and pedred_bit:
            pedgreen = 0
            pedred = 0
            pedgreenflash = 1
        else:
            pedgreen = pedgreen_bit
            pedred = pedred_bit
            pedgreenflash = 0
        
        status_dict = {
            "allred": status_list[0] if len(status_list) > 0 else 0,
            "yellow": status_list[1] if len(status_list) > 1 else 0,
            "green": status_list[2] if len(status_list) > 2 else 0,
            "turnleft": status_list[3] if len(status_list) > 3 else 0,
            "straight": status_list[4] if len(status_list) > 4 else 0,
            "turnright": status_list[5] if len(status_list) > 5 else 0,
            "pedgreen": pedgreen,
            "pedred": pedred,
            "pedgreenflash": pedgreenflash,
        }
        signal_status_details.append(status_dict)
    
    return signal_status_details

def process_5fc0_control_strategy(control_strategy):
    """處理5FC0控制策略位"""
    return {
        "fixed_time": bool(control_strategy & CS_FIXED_TIME),
        "dynamic": bool(control_strategy & CS_DYNAMIC),
        "intersection_manual": bool(control_strategy & CS_INTERSECTION_MANUAL),
        "central_manual": bool(control_strategy & CS_CENTRAL_MANUAL),
        "phase_control": bool(control_strategy & CS_PHASE_CONTROL),
        "immediate_control": bool(control_strategy & CS_IMMEDIATE_CONTROL),
        "actuated": bool(control_strategy & CS_ACTUATED),
        "special_route": bool(control_strategy & CS_SPECIAL_ROUTE),
    }

# 5F 群組封包定義
F5_GROUP_DEFINITIONS = {
    "5F03": {
        "name": "時相資料維管理",
        "description": "主動回報號誌控制器步階轉換之資料",
        "reply_type": "主動回報",
        "needs_ack": False,
        "group": "5F",
        "command": 0x03,
        
        # 统一字段列表，按顺序定义，使用 index 表示位置
        "fields": [
            {"name": "phase_order", "index": 0, "type": "uint8", "description": "時相編號"},
            
            # signal_map 直接轉換為列表，不顯示原始值
            {
                "name": "signal_map",
                "index": 1,
                "type": "uint8",
                "description": "號誌位置圖",
                "post_process": lambda value, result: int_to_binary_list(value)
                # 結果：signal_map = [1, 0, 1, 0, 1, 0, 1, 0] 而不是 85
            },
            
            {"name": "signal_count", "index": 2, "type": "uint8", "description": "信號燈數量"},
            {"name": "sub_phase_id", "index": 3, "type": "uint8", "description": "分相序號"},
            {"name": "step_id", "index": 4, "type": "uint8", "description": "步階序號"},
            {"name": "step_sec", "index": 5, "type": "uint16", "endian": "big", "description": "步階秒數"},
            
            # signal_status 直接轉換為詳細狀態，不顯示原始列表
            {
                "name": "signal_status",
                "index": 7,
                "type": "list",
                "item_type": "uint8",
                "count_from": "signal_count",
                "description": "信號狀態列表",
                "post_process": lambda value, result: process_5f03_signal_status(value)
                # 結果：signal_status = [詳細狀態字典列表] 而不是 [129, 196, 129, 196]
            }
        ],
        
        "validation": {
            "type": "min_length",
            "value": 7,
            "error_message": "5F03資料長度不足"
        }
    },
    
    "5F08": {
        "name": "現場操作回報",
        "description": "回報號誌控制器現場操作",
        "reply_type": "主動回報",
        "needs_ack": False,
        "group": "5F",
        "command": 0x08,
        
        "fields": [
            {
                "name": "field_operate",
                "index": 0,  # PAYLOAD[0]
                "type": "uint8",
                "description": "現場操作碼",
                # 自定義映射
                "mapping": {
                    0x01: "現場手動",
                    0x02: "現場全紅",
                    0x40: "現場閃光",
                    0x80: "上次現場操作回復"
                },
                # 後處理：格式化輸出
                "post_process": lambda value, result: f"0x{value:02X}H ({result.get('_mapping_desc', '未知')})"
            }
        ],
        
        "validation": {
            "type": "exact_length",
            "value": 1,
            "error_message": "5F08資料長度錯誤"
        }
    },
    
    "5FC8": {
        "name": "時制計畫回報",
        "description": "回報目前時制計畫內容",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0xC8,
        
        "fields": [
            {
                "name": "plan_id",
                "index": 0,
                "type": "uint8",
                "description": "時制計畫編號"
            },
            {
                "name": "direct",
                "index": 1,
                "type": "uint8",
                "description": "基準方向"
            },
            {
                "name": "phase_order",
                "index": 2,
                "type": "uint8",
                "description": "時相種類編號"
            },
            {
                "name": "sub_phase_count",
                "index": 3,
                "type": "uint8",
                "description": "綠燈分相數"
            },
            {
                "name": "greens",
                "index": 4,  # PAYLOAD[4] 開始
                "type": "list",
                "item_type": "uint8",
                "count_from": "sub_phase_count",  # 依賴 sub_phase_count
                "description": "各分相綠燈時間"
            },
            {
                "name": "cycle_time",
                "index": None,  # 使用 current_index（自動跟蹤）
                "type": "uint16",
                "endian": "big",
                "description": "週期秒數"
            },
            {
                "name": "offset",
                "index": None,  # 使用 current_index（自動跟蹤）
                "type": "uint16",
                "endian": "big",
                "description": "時差秒數"
            }
        ],
        
        "validation": {
            "type": "min_length",
            "value": 4,
            "error_message": "5FC8資料長度不足"
        }
    },
    
    "5FC6": {
        "name": "一般日時段型態查詢回報",
        "description": "週內日時段切分內容",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "5F",
        "command": 0xC6,
        
        "fields": [
            {
                "name": "segment_type",
                "index": 0,
                "type": "uint8",
                "description": "時段類型"
            },
            {
                "name": "segment_count",
                "index": 1,
                "type": "uint8",
                "description": "時段數量"
            },
            {
                "name": "segment_list", #(Hour+Min+PlanID)(segment_count)
                "index": 2,  # PAYLOAD[2] 開始
                "type": "struct_list",
                "item_fields": [
                    {"name": "hour", "type": "uint8"},
                    {"name": "minute", "type": "uint8"},
                    {"name": "plan_id", "type": "uint8"}
                ],
                "count_from": "segment_count",
                "description": "時段列表"
            },
            {
                "name": "num_weekday",
                "index": None, # 使用 current_index（自動跟蹤）
                "type": "uint8",
                "description": "星期數量"
            },
            {
                "name": "weekday_list",
                "index": None, # 使用 current_index（自動跟蹤）
                "type": "list",
                "item_type": "uint8",
                "count_from": "num_weekday",
                "index_calc": lambda result: 2 + result.get("segment_count", 0) * 3 + 1,
                "description": "星期列表"
            }
        ],
        
        "validation": {
            "type": "min_length",
            "value": 2,
            "error_message": "5FC6資料長度不足"
        }
    }
}

