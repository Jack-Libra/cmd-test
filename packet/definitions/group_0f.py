"""
0F 群组封包定义
"""
from core.utils import int_to_binary_list

def format_0f04_hardware_status(hardware_status):
    """格式化0F04硬體狀態為字符串列表"""
    # 將 16 bits 轉換為二進制列表（低位在前）
    low_byte = hardware_status & 0xFF
    high_byte = (hardware_status >> 8) & 0xFF
    status_bits = int_to_binary_list(low_byte) + int_to_binary_list(high_byte)
    
    formatted_lines = []
    status_map = [
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
    
    for bit_pos, description in status_map:
        if bit_pos < len(status_bits) and status_bits[bit_pos]:
            formatted_lines.append(f"   狀態 {bit_pos}: {description}")
    
    # 如果沒有任何錯誤，顯示正常
    if not formatted_lines:
        formatted_lines.append("   狀態: 系統正常")
    
    return formatted_lines
def format_0f81_error_code(error_code, result=None):
    """格式化0F81錯誤碼為字符串列表"""
    param_num = result.get("param_num", 0) if result else 0
    errors = process_0f81_errors(error_code)
    
    formatted_lines = []
    
    if errors.get("invalid_msg"):
        formatted_lines.append("   錯誤: 無此訊息")
    if errors.get("no_response"):
        formatted_lines.append("   錯誤: 無法回應資料")
    if errors.get("param_invalid"):
        formatted_lines.append(f"   錯誤: 參數值無效(位置:{param_num})")
    if errors.get("no_param"):
        formatted_lines.append(f"   錯誤: 位元組總參數數目錯誤(錯誤值:{param_num})")
    if errors.get("prep_error"):
        formatted_lines.append("   錯誤: 設備類別錯誤")
    if errors.get("timeout"):
        formatted_lines.append("   錯誤: 逾時")
    if errors.get("exceed_limit"):
        formatted_lines.append(f"   錯誤: 參數值超過硬體限制(位置:{param_num})")
    if errors.get("reported"):
        formatted_lines.append("   錯誤: 已被訊息等級設定排除")
    
    # 如果沒有任何錯誤描述，顯示未知錯誤
    if not formatted_lines:
        formatted_lines.append(f"   錯誤: 未知錯誤(錯誤碼:0x{error_code:02X})")
    
    return formatted_lines
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
        "description": "回報設定訊息有效",
        "reply_type": "設定回報",
        "needs_ack": True,  # 需要发送 ACK
        "group": "0F",
        "command": 0x80,
        "log_modes": ["receive", "command"],
        "fields": [
            {
                "name": "command_id",
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
                "name": "command_id",
                "index": 2,  # payload[2] 和 payload[3]
                "type": "uint16",
                "endian": "big",
                "description": "指令ID (2 bytes: 設備碼 + 指令碼)"
            },
            {
                "name": "error_code",
                "index": 4,  # payload[4]
                "type": "uint8",
                "description": "錯誤代碼",
                "post_process": format_0f81_error_code
            },
            {
                "name": "param_num",
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
                "name": "hardware_status",
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
        "log_modes": ["receive"],
        "fields": [],
        
        "validation": {
            "type": "min_length",
            "value": 9,
            "error_message": "0F02資料長度不足"
        }
    }
}

