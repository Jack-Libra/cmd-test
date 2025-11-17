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
│ ├── network.py # 網路層（UDP傳輸）
│ └── log_setup.py # 日誌配置
│
├── packet/ # 核心封包處理模組
│ ├── center.py # 封包處理中心（統一管理）
│ ├── packet_parser.py # 封包解析器
│ ├── packet_builder.py # 封包構建器
│ ├── packet_processor.py # 封包處理器（日誌、格式化）
│ ├── packet_definition.py # 封包定義與字段類型管理
│ └── definitions/ # 封包定義文件
│ ├── group_5f.py # 5F 群組定義
│ └── group_0f.py # 0F 群組定義
│
├── command/ # 指令處理模組
│ ├── session_manager.py # 多步驟會話管理
│ └── step_processor.py # 步驟處理與參數驗證
│
└── logs/ # 日誌目錄
├── receive.log # 接收模式日誌
└── command.log # 命令模式日誌
```


## 架構特點

### 1. 分層架構
- **應用層**：`mode.py` (Receive/Command 模式)
- **指令處理層**：`command/` (會話管理、步驟處理)
- **封包處理層**：`packet/` (解析、構建、處理)
- **網路層**：`config/network.py` (UDP 傳輸)

### 2. 統一資源管理
- **PacketDefinition 單例**：通過 `PacketCenter` 統一管理，所有組件共享同一個實例
- **依賴注入**：`PacketBuilder`、`PacketParser`、`PacketProcessor` 通過構造函數接收 `packet_def`
- **日誌統一**：使用統一的 logger 實例，避免重複創建

### 3. 多步驟指令輸入
- **會話管理**：`SessionManager` 管理多步驟輸入的狀態
- **步驟處理**：`StepProcessor` 處理每步的輸入驗證和提示生成
- **參數解析**：統一的 `parse_input` 方法支持 dec/hex/binary 多種輸入格式
- **範圍驗證**：統一的 `validate_param_range` 方法驗證參數範圍

### 4. 定義驅動設計
- **字段類型系統**：`FIELD_TYPES` 定義了 parser、builder、input_parsers 三種操作
- **指令定義擴展**：通過 `interaction_type` 和 `steps` 支持多步驟輸入
- **易於擴展**：新增指令只需在 `definitions/` 中添加定義

## 運行模式

### Receive 模式
只接收數據包，記錄日誌，發送 ACK

```bash
python main.py --mode receive
```

### Command 模式
接收數據包 + 命令下傳，記錄日誌，追蹤指令狀態

```bash
python main.py --mode command
```

**Command 模式功能**：
- 單步指令輸入：`5F10 1 60`
- 多步驟指令輸入：`5F13` (會引導完成多步輸入)
- 指令狀態追蹤：自動追蹤指令發送和響應
- 指令歷史：`history` 命令查看歷史記錄

## 支持的封包類型

### 5F 群組（號控）
- **5F03**: 時相資料庫管理（主動回報）
- **5F08**: 現場操作回報（主動回報）
- **5F0C**: 時相步階變換控制管理（主動回報）
- **5F10**: 目前控制策略管理（設定）
- **5F13**: 時相資料庫管理（設定，支持多步驟輸入）
- **5F40**: 目前控制策略管理（查詢）
- **5F48**: 目前時制計畫管理（查詢）
- **5FC0**: 控制策略回報（主動回報）
- **5FC6**: 一般日時段型態查詢回報
- **5FC8**: 時制計畫回報（查詢回報）

### 0F 群組（共用）
- **0F04**: 設備硬體狀態管理（主動回報）
- **0F80**: 設定回報（有效）
- **0F81**: 設定/查詢回報（無效）
- **0FC0**: 查詢現場設備編號回報
- **0F02**: 回報終端設備現場手動更改時間

## 指令輸入格式

### 單步輸入
```bash
# 十進制
5F10 1 60

# 十六進制（字段定義中指定 input_type: "hex"）
5F40 0x01

# 二進制（字段定義中指定 input_type: "binary"）
5F10 10101010
```

### 多步驟輸入
```bash
# 啟動多步驟指令
5F13

# 步驟 1: 輸入基本參數
40 10101010 8 3

# 步驟 2: 輸入列表值（24個值）
85 85 85 ... (共24個)

# 步驟 3: 確認
y
```

### 指令管理命令
- `help`: 顯示幫助信息
- `status`: 顯示當前狀態
- `history`: 顯示指令歷史
- `cancel`: 取消當前多步驟輸入
- `quit`: 退出程序

## 核心組件說明

### PacketCenter
封包處理中心，統一管理：
- `PacketDefinition`: 封包定義（單例）
- `PacketParser`: 封包解析
- `PacketBuilder`: 封包構建
- `PacketProcessor`: 封包處理

### PacketDefinition
封包定義管理器：
- `get_definition()`: 獲取指令定義
- `get_field_type()`: 獲取字段類型定義
- `get_field_definition()`: 獲取字段定義
- `parse_input()`: 從用戶輸入解析參數值

### SessionManager
多步驟會話管理：
- `create_session()`: 創建會話
- `get_active_session()`: 獲取活動會話
- `update_session()`: 更新會話
- `remove_session()`: 移除會話
- 自動清理過期會話（默認 5 分鐘超時）

### StepProcessor
步驟處理器：
- `get_step_prompt()`: 生成步驟提示
- `process_step()`: 處理步驟輸入
- 參數解析和驗證
- 動態列表字段處理


## 待實現

- **共享接收線程**
- **UDP代理**