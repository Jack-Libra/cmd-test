"""
0F 群组封包定义
"""
from utils import int_to_binary_list
from config.constants import HARDWARE_STATUS_MAP, ERROR_CODE_MAP


def format_0f04_hardware_status(hardware_status):
    """格式化0F04硬體狀態為字符串列表"""
    # 將 16 bits 轉換為二進制列表（低位在前）
    low_byte = hardware_status & 0xFF
    high_byte = (hardware_status >> 8) & 0xFF
    status_bits = int_to_binary_list(low_byte) + int_to_binary_list(high_byte)
    
    formatted_lines = []
      
    for bit_pos, description in HARDWARE_STATUS_MAP:
        if bit_pos < len(status_bits) and status_bits[bit_pos]:
            formatted_lines.append(f"   狀態 {bit_pos}: {description}")
    
    if not formatted_lines:
        formatted_lines.append("   狀態: 系統正常")
    
    return formatted_lines


# 0F 群組封包定義
F0_GROUP_DEFINITIONS = {
    "0F80": {
        "name": "設定回報（有效）",
        "description": "回報設定訊息有效",
        "reply_type": "設定回報",
        "needs_ack": True,  # 需要发送 ACK
        "group": "0F",
        "command": 0x80,
        "log_modes": ["receive", "command"],
        "fields": [
            {
                "name": "指令ID",
                "index": 2,  # payload[2] 和 payload[3] 组成 command_id (2 bytes)
                "type": "uint16",
                "endian": "big",
                "description": "指令ID (2 bytes: 設備碼 + 指令碼)"
            }
        ],
        "validation": {
            "type": "min_length",
            "value": 4,  # 0F + 80 + CommandID(2) = 4 bytes
            "error_message": "0F80資料長度不足"
        }
    },
    
    "0F81": {
        "name": "設定/查詢回報（無效）",
        "description": "回報設定或查詢訊息無效",
        "reply_type": "設定回報",
        "needs_ack": True,  # 需要发送 ACK
        "group": "0F",
        "command": 0x81,
        "log_modes": ["receive", "command"],
        "fields": [
            {
                "name": "指令ID",
                "index": 2,  # payload[2] 和 payload[3]
                "type": "uint16",
                "endian": "big",
                "description": "指令ID (2 bytes: 設備碼 + 指令碼)"
            },
            {
                "name": "錯誤碼",
                "index": 4,  # payload[4]
                "type": "uint8",
                "description": "錯誤代碼",
                "mapping": ERROR_CODE_MAP
            },
            {
                "name": "參數編號",
                "index": 5,  # payload[5]
                "type": "uint8",
                "description": "發生第一個錯誤參數值之位址或參數數目錯誤值"
            }
        ],
        "validation": {
            "type": "min_length",
            "value": 6,  # 0F + 81 + CommandID(2) + ErrorCode(1) + ParamNum(1) = 6 bytes
            "error_message": "0F81資料長度不足"
        }
    },
    
    "0F04": {
        "name": "設備硬體狀態管理",
        "description": "現場設備回報狀態",
        "reply_type": "主動回報",
        "needs_ack": False,
        "group": "0F",
        "command": 0x04,
        "log_modes": ["receive"],
        "fields": [
            {
                "name": "硬體狀態碼",
                "index": 2,  # PAYLOAD[2] 開始（0F 04 之後）
                "type": "uint16",
                "endian": "big",
                "description": "硬體狀態碼（16 bits）",
                "post_process": format_0f04_hardware_status
            }
        ],
        "validation": {
            "type": "min_length",
            "value": 4,  # 0F + 04 + 2 bytes 狀態碼 = 4 bytes
            "error_message": "0F04資料長度不足"
        }
    },
    
    "0FC0": {
        "name": "查詢現場設備編號回報",
        "description": "查詢現場設備編號回報",
        "reply_type": "查詢回報",
        "needs_ack": True,
        "group": "0F",
        "command": 0xC0,
        "log_modes": ["receive","command"],
        "fields": [
            {
                "name": "設備序號",
                "offset": 9,
                "type": "uint8",
                "description": "設備序號"
            },
            {
                "name": "子設備數目",
                "offset": 10,
                "type": "uint8",
                "description": "子設備數目"
            },
            {
                "name": "子設備序號",
                "offset": 11,
                "type": "uint8",
                "description": "子設備序號"
            },
            {
                "name": "設備編號",
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
        "log_modes": ["receive"],
        "fields": [],
        
        "validation": {
            "type": "min_length",
            "value": 9,
            "error_message": "0F02資料長度不足"
        }
    }
}

