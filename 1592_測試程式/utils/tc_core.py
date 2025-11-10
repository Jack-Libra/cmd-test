"""
交通控制系統核心模組
"""
import datetime
from .log_setup import *

# 協議常量
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

COMMAND_REGISTRY = {
    # "5F00": {
    #     "name": "自動回報控制策略之目前執行內容",
    #     "hex": 0x00,
    #     "parser": "parse_5f00_packet",
    #     "processor": "process_5f00_packet"
    # },
    "5F03": {
        "name": "主動回報號誌控制器步階轉換之資料",
        "hex": 0x03,
        "parser": "parse_5f03_packet",
        "processor": "process_5f03_packet"
    },
    "5F08": {
        "name": "回報號誌控制器現場操作", 
        "hex": 0x08,
        "parser": "parse_5f08_packet",
        "processor": "process_5f08_packet"
    },
    "5F10": {
        "name": "控制策略設定",
        "hex": 0x10,
        "parser": "parse_5f10_packet", 
        "processor": "process_5f10_packet"
    },
    "5FC6": {
        "name": "週內日時段切分內容",
        "hex": 0xC6,
        "parser": "parse_5fc6_packet",
        "processor": "process_5fc6_packet"
    },
    "5F40": {
        "name": "查詢控制策略",
        "hex": 0x40,
        "parser": "parse_5f40_packet",
        "processor": "process_5f40_packet"
    },
    "5FC0": {
        "name": "控制策略回報", 
        "hex": 0xC0,
        "parser": "parse_5fc0_packet",
        "processor": "process_5fc0_packet"
    },
    "0F80": {
        "name": "指令成功回應",
        "hex": 0x80,
        "parser": "parse_0f80_packet",
        "processor": "process_0f80_packet"
    },
    "0F81": {
        "name": "指令失敗回應", 
        "hex": 0x81,
        "parser": "parse_0f81_packet",
        "processor": "process_0f81_packet"
    },
    "0F04": {
        "name": "系統狀態回報",
        "hex": 0x04,
        "parser": "parse_0f04_packet",
        "processor": "process_0f04_packet"
    },
    "0FC0": {
        "name": "查詢現場設備編號回報",
        "hex": 0xC0,
        "parser": "parse_0fc0_packet",
        "processor": "process_0fc0_packet"
    },
    "0F02": {
        "name": "回報終端設備現場手動更改時間",
        "hex": 0x02,
        "parser": "parse_0f02_packet",
        "processor": "process_0f02_packet"
    },
    "5F0C": {
        "name": "時相步階變換回報",
        "hex": 0x0C,
        "parser": "parse_5f0c_packet",
        "processor": "process_5f0c_packet"
    },
    "5FC8": {
        "name": "回報目前時制計畫內容",
        "hex": 0xC8,
        "parser": "parse_5fc8_packet",
        "processor": "process_5fc8_packet"
    }
}

def int_to_binary_list(n):
    """將整數轉換為二進位列表"""
    if n == 0:
        return [0] * 8
    binary_str = format(n, '08b')
    reverse_str = binary_str[::-1]
    return [int(bit) for bit in reverse_str]

def get_day_type():
    """取得今天的類型"""
    today = datetime.datetime.now()
    weekday = today.weekday()
    if weekday < 5:
        return 'weekday'
    else:
        return 'weekend'

def get_control_strategy_desc(strategy_details):
    """從控制策略詳細資訊獲取描述文字"""
    result = []
    
    strategy_map = {
        "fixed_time": "定時控制",
        "dynamic": "動態控制", 
        "intersection_manual": "路口手動",
        "central_manual": "中央手動",
        "phase_control": "時相控制",
        "immediate_control": "即時控制",
        "actuated": "觸動控制",
        "special_route": "特別路線控制"
    }
    
    for key, desc in strategy_map.items():
        if strategy_details.get(key, False):
            result.append(desc)
    
    return "、".join(result) if result else "無設定策略"

def print_packet_info(packet):
    """統一的封包資訊顯示函數"""
    if not packet:
        return
    
    command = packet.get("command", "Unknown")
    tc_id = packet.get("tc_id", 0)
    
    log_info(f"=== 封包詳細資訊 ===")
    log_info(f"序列號 (SEQ): 0x{packet.get('seq', 0):02X}")
    log_info(f"控制器編號: TC{tc_id:03d}")
    log_info(f"指令: {command}")
    
    # 根據指令類型顯示詳細資訊
    if command in COMMAND_REGISTRY:
        command_info = COMMAND_REGISTRY[command]
        _display_packet_details(packet, command)
    
    log_info(f"原始資料: {packet.get('raw_data', '')}")
    log_info(f"接收時間: {packet.get('timestamp', '')}")

def _display_packet_details(packet, command):
    """顯示特定指令的詳細資訊 (修正版 - 包含行人綠閃邏輯)"""
    if command == "5F03":
        phase_order = packet.get('phase_order', 0)
        log_info(f"時相編號: {phase_order:02X}".upper())
        signal_map = packet.get('signal_map', 0)
        signal_map_list = packet.get('signal_map_list', [])
        log_info(f"號誌位置圖: 0x{signal_map:02X} = {signal_map_list}")
        log_info(f"信號燈數量: {packet.get('signal_count', 0)}")
        log_info(f"分相序號: {packet.get('sub_phase_id', 0)}")
        log_info(f"步階序號: {packet.get('step_id', 0)}")
        log_info(f"步階秒數: {packet.get('step_sec', 0)} 秒")

        for i, status in enumerate(packet.get('signal_status_details', [])):
            status_str = []

            # 車輛燈號檢查
            if status.get("allred", 0):
                status_str.append("全紅")
            if status.get("yellow", 0):
                status_str.append("黃燈")
            if status.get("green", 0):
                status_str.append("綠燈")
            if status.get("turnleft", 0):
                status_str.append("左轉")
            if status.get("straight", 0):
                status_str.append("直行")
            if status.get("turnright", 0):
                status_str.append("右轉")

            if status.get("pedgreenflash", 0):
                status_str.append("行人綠閃")
            elif status.get("pedgreen", 0):
                status_str.append("行人綠燈")
            elif status.get("pedred", 0):
                status_str.append("行人紅燈")

            status_desc = "、".join(status_str) if status_str else "無燈號"
            log_info(f"  方向 {i+1}: {status_desc}")

    elif command == "5FC0":
        strategy_details = packet.get("control_strategy_details", {})
        log_info(f"控制策略碼: 0x{packet.get('control_strategy', 0):02X}")
        log_info(f"控制策略說明: {get_control_strategy_desc(strategy_details)}")
        log_info(f"有效時間: {packet.get('effect_time', 0)} 分鐘")

    elif command == "5F08":
        log_info(f"現場操作狀態: {packet.get('field_operate', '未知')}")

    elif command == "0F04":
        log_info(f"系統狀態: 0x{packet.get('system_status', 0):04X}")
        log_info(f"狀態描述: {packet.get('status_description', '未知')}")