# 交通控制系統

## 項目結構

```
traffic_control/
├── main.py # 主程序入口
├── mode.py # 運行模式管理（Receive, Command）
├── utils.py # 共用工具函數
│
├── config/ # 配置環境相關
│ ├── config.py # 配置管理器
│ ├── constants.py # 協議常量定義
│ ├── network.py # 網路層
│ └── log_setup.py # 日誌配置
│
├── packet/  # 核心模組
│ ├── registry.py # 封包中心
│ ├── packet_parser.py # 封包解析器
│ ├── packet_builder.py # 封包建構器
│ ├── packet_processor.py # 封包處理器
│ ├── packet_definition.py # 封包定義
│ └── definitions/
│ ├────── group_5f.py # 5F 群組定義
│ └────── group_0f.py # 0F 群組定義
│
└── logs/ 
├── receive.log # 接收模式日誌
└── command.log # 命令模式日誌
```

## 特點
1. **雙模式+日誌隔離**：日誌根據不同模式記錄不同封包
2. **分隔封包定義與解析、處理**


## 運行模式
- **Receive 模式**：只接收數據包，紀錄日誌，發送ACK
python main.py --mode receive

- **Command 模式**：接收數據包 + 命令下傳，紀錄日誌
python main.py --mode command


## 支持的封包類型

### 5F 群組（號控）
- **5F03**: 時相資料庫管理（主動回報）
- **5F08**: 現場操作回報（主動回報）
- **5F0C**: 時相步階變換控制管理（主動回報）
- **5F10**: 目前控制策略管理（設定）
- **5F40**: 目前控制策略管理（查询）
- **5F48**: 目前時制計畫管理（查询）
- **5FC0**: 控制策略回報（主動回報）
- **5FC6**: 一般日時段型態查詢回報
- **5FC8**: 時制計畫回報（查詢回報）

### 0F 群組（共用）
- **0F04**: 設備硬體狀態管理（主動回報）
- **0F80**: 設定回報（有效）
- **0F81**: 設定/查詢回報（無效）
- **0FC0**: 查詢現場設備編號回報
- **0F02**: 回報終端設備現場手動更改時間



## 待實現

- **共享接收線程**
- **UDP代理**
