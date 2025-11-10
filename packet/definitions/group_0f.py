"""
0F 群组封包定义
"""

def process_0f81_errors(error_code):
    """處理0F81錯誤碼"""
    return {
        "invalid_msg": bool(error_code & 0x01),
        "no_response": bool(error_code & 0x02),
        "param_invalid": bool(error_code & 0x04),
        "no_param": bool(error_code & 0x08),
        "prep_error": bool(error_code & 0x10),
        "timeout": bool(error_code & 0x20),
        "exceed_limit": bool(error_code & 0x40),
        "reported": bool(error_code & 0x80)
    }

# 0F 群組封包定義
F0_GROUP_DEFINITIONS = {
    "0F80": {
        "name": "設定回報（有效）",
        "description": "指令成功回應",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "0F",
        "command": 0x80,
        
        "fields": [
            {
                "name": "command_id",
                "offset": 9,
                "type": "uint16",
                "endian": "big",
                "description": "指令ID"
            }
        ],
        
        "validation": {
            "type": "min_length",
            "value": 11,
            "error_message": "0F80資料長度不足"
        },
        
        "post_process": lambda result: {
            **result,
            "valid": True
        }
    },
    
    "0F81": {
        "name": "設定/查詢回報（無效）",
        "description": "指令失敗回應",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "0F",
        "command": 0x81,
        
        "fields": [
            {
                "name": "command_id",
                "offset": 9,
                "type": "uint16",
                "endian": "big",
                "description": "指令ID"
            },
            {
                "name": "error_code",
                "offset": 11,
                "type": "uint8",
                "description": "錯誤代碼"
            },
            {
                "name": "param_num",
                "offset": 12,
                "type": "uint8",
                "optional": True,
                "description": "參數編號"
            }
        ],
        
        "validation": {
            "type": "min_length",
            "value": 12,
            "error_message": "0F81資料長度不足"
        },
        
        "post_process": lambda result: {
            **result,
            "valid": False,
            "errors": process_0f81_errors(result.get("error_code", 0))
        }
    },
    
    "0F04": {
        "name": "系統狀態回報",
        "description": "系統狀態回報",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "0F",
        "command": 0x04,
        
        "fields": [
            {
                "name": "system_status",
                "offset": 9,
                "type": "uint16",
                "endian": "big",
                "description": "系統狀態碼"
            }
        ],
        
        "validation": {
            "type": "min_length",
            "value": 11,
            "error_message": "0F04資料長度不足"
        },
        
        "post_process": lambda result: {
            **result,
            "status_description": {
                0x4100: "系統正常運行",
                0x4200: "系統警告狀態",
                0x4300: "系統異常狀態",
                0x0000: "未知狀態"
            }.get(result.get("system_status", 0), 
                  f"未定義狀態(0x{result.get('system_status', 0):04X})")
        }
    },
    
    "0FC0": {
        "name": "查詢現場設備編號回報",
        "description": "查詢現場設備編號回報",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "0F",
        "command": 0xC0,
        
        "fields": [
            {
                "name": "equipment_no",
                "offset": 9,
                "type": "uint8",
                "description": "設備序號"
            },
            {
                "name": "sub_count",
                "offset": 10,
                "type": "uint8",
                "description": "子設備數目"
            },
            {
                "name": "sub_equipment_no",
                "offset": 11,
                "type": "uint8",
                "description": "子設備序號"
            },
            {
                "name": "equipment_id",
                "offset": 12,
                "type": "uint8",
                "optional": True,
                "description": "設備編號"
            }
        ],
        
        "validation": {
            "type": "min_length",
            "value": 12,
            "error_message": "0FC0資料長度不足"
        }
    },
    
    "0F02": {
        "name": "回報終端設備現場手動更改時間",
        "description": "回報終端設備現場手動更改時間",
        "reply_type": "主動回報",
        "needs_ack": False,
        "group": "0F",
        "command": 0x02,
        
        "fields": [],
        
        "validation": {
            "type": "min_length",
            "value": 9,
            "error_message": "0F02資料長度不足"
        }
    }
}

