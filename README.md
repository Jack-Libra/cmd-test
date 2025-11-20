# 交通控制系統

## 項目結構

```
traffic_control/
├── src/
│   └── traffic_control/
│       ├── main.py
│       ├── mode.py   #模式    
│       ├── utils.py  #共用含式、底層解碼
│       ├── definitions/    #定義層
│       │   ├── __init__.py
│       │   ├── group_5f.py
│       │   └── group_0f.py
│       ├── packet/   #封包相關核心組件
│       │   ├── __init__.py
│       │   ├── center.py      #中心 facade
│       │   ├── packet_parser.py  #解析層
│       │   ├── packet_builder.py #構建層
│       │   ├── packet_processor.py #處裡層
│       │   └── packet_definition.py #定義集合
│       ├── command/
│       │   ├── __init__.py
│       │   ├── session_manager.py #會話
│       │   └── step_processor.py  #步驟處理
│       └── config/
│           ├── __init__.py
│           ├── config.py   #環境配置相關   
│           ├── constants.py #協議相關常量
│           ├── network.py   #網路層
│           └── log_setup.py  #日誌管理
├── tests/
│   ├── __init__.py
│   ├── test_packet.py
│   └── ...
├── pyproject.toml   #待實現 
├── README.md
└── logs/        #自動產生          
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
python src/traffic_control/main.py -m receive
```

### Command 模式
接收數據包 + 命令下傳，記錄日誌，追蹤指令狀態

```bash
python src/traffic_control/main.py -m command
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
- `cancel`: 取消當前多步驟輸入
- `q`: 退出程序

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


## 接收封包流程

封包從 UDP 接收後，經過以下處理流程：

### 1. UDP 接收層 (`config/network.py`)
- **接收數據**：`network.receive_data()` 從 UDP socket 接收原始字節數據
- **緩衝處理**：`PacketBuffer.feed()` 處理接收到的數據
  - 尋找封包起始標記（DLE+STX 或 DLE+ACK）
  - 根據封包類型計算長度（STX 從 LEN 字段，ACK 固定 8 bytes）
  - 切割出完整封包幀，返回封包列表

### 2. 封包解碼層 (`utils.py`)
- **解碼封包**：`decode(frame)` 處理原始幀數據
  - 驗證 DLE 標記（必須為 0xAA）
  - 識別封包類型（STX/ACK）
  - **校驗和驗證**：計算 XOR 校驗和，驗證封包完整性
  - **提取基礎字段**：
    - `seq`: 序列號（1 byte）
    - `addr`: 控制器地址（2 bytes, big-endian）
    - `len`: 封包長度（2 bytes, big-endian）
  - **STX 封包處理**：
    - 提取 PAYLOAD 字段（位於 DLE ETX 之間）
    - **DLE 反溢出處理**：將 `0xAA 0xAA` 還原為單個 `0xAA`
  - **ACK 封包處理**：僅包含確認信息，無 PAYLOAD

### 3. 封包解析層 (`packet/packet_parser.py`)
- **解析封包**：`PacketParser.parse()` 解析解碼後的數據
  - **ACK 封包**：直接創建 `Packet` 對象，標記 `reply_type="ACK"`
  - **STX 封包處理**：
    - 從 PAYLOAD 前 2 bytes 提取指令碼（如 `5F10`）
    - 創建基礎 `Packet` 對象（包含 seq、tc_id、length、cmd_code、raw_packet）
    - **查找定義**：從 `PacketDefinition` 獲取指令定義
    - **字段解析**：`FieldParser.parse_fields()` 根據定義解析各字段
      - 支持類型：`uint8`、`uint16`、`list`、`time_segment_list`、`weekday_list`、`signal_map`、`signal_status_list`
      - 解析結果存入 `packet.extra_fields`（中文字段名）
      - 設置 `packet.command`（指令名稱）和 `packet.reply_type`（訊息型態）

### 4. 封包處理層 (`packet/packet_processor.py`)
- **處理封包**：`PacketProcessor.process()` 處理解析後的封包
  - 根據 `cmd_code` 查找對應的 handler（如 `_handle_5f03`）
  - Handler 從 `packet.extra_fields` 提取字段值
  - **字段映射**：應用預定義的映射規則（如數值到中文描述）
  - **格式化輸出**：使用 `format_packet_display()` 生成結構化日誌
  - 記錄到日誌文件

### 5. ACK 回應 (`packet/center.py`)
- **發送 ACK**：`PacketCenter.process()` 處理完封包後
  - 使用 `encode(seq, addr, b"")` 構建 ACK 封包
  - 通過 `network.send_data()` 發送回源地址
  - ACK 封包格式：`DLE ACK SEQ ADDR(2) LEN(2) CKS`

### 解析結果
封包解析後，`Packet` 對象包含：
- **基礎信息**：seq、tc_id、length、cmd_code、raw_packet、receive_time
- **指令信息**：command（指令名稱）、reply_type（訊息型態）
- **解析字段**：`extra_fields` 字典，包含所有解析後的中文字段名和對應值
  - 例如：`{"時相編號": 1, "號誌位置圖": SignalMap(0xC0), "燈號狀態列表": SignalStatusList([...])}`

## 下傳封包流程

指令從用戶輸入到下傳到號誌控制器的完整流程：

### 1. 指令輸入層 (`mode.py` - `Command._command_loop()`)
- **接收用戶輸入**：從終端讀取指令（如 `5F10 1 60`）
- **指令識別**：解析指令碼（如 `5F10`）
- **查找定義**：從 `PacketDefinition` 獲取指令定義
- **驗證類型**：確認指令為「查詢」或「設定」類型

### 2. 會話管理層 (`command/session_manager.py`)
- **創建會話**：`SessionManager.create_session()` 為指令創建會話對象
  - 存儲指令碼、定義、已輸入的字段值
  - 支持多步驟輸入（如 `5F13` 需要多步完成）
  - 會話超時管理（默認 5 分鐘）

### 3. 步驟處理層 (`command/step_processor.py`)
- **步驟驗證**：`StepProcessor.process_step()` 處理每步輸入
  - **參數解析**：支持十進制、十六進制、二進制輸入格式
  - **範圍驗證**：使用 `validate_param_range()` 驗證參數範圍
  - **動態列表處理**：根據已輸入參數計算列表長度（如 `count_from`）
  - **步驟提示**：`get_step_prompt()` 生成當前步驟的輸入提示
- **完成檢查**：所有步驟完成後，返回完整的 `fields` 字典

### 4. 封包構建層 (`packet/packet_builder.py`)
- **構建 PAYLOAD**：`PacketBuilder.build()` 構建封包
  - **添加指令碼**：根據群組（5F/0F）添加群組碼和命令碼
  - **構建字段**：`FieldBuilder.build_field()` 將字段值轉換為字節
    - 支持類型：`uint8`、`uint16`、`list`（列表字段）
    - 使用 `FIELD_TYPES` 中定義的 `builder` 函數進行轉換
  - **組合 PAYLOAD**：按定義順序組合所有字段字節

### 5. 封包編碼層 (`utils.py`)
- **編碼封包**：`encode(seq, addr, payload)` 編碼封包
  - **生成序列號**：`PacketCenter.next_seq()` 線程安全地獲取下一個序列號
  - **DLE 溢出處理**：`escape_dle()` 將 PAYLOAD 中的 `0xAA` 轉換為 `0xAA 0xAA`
  - **構建封包結構**：
    - Header: `DLE STX SEQ ADDR(2) LEN(2)`
    - Payload: 經過 DLE 溢出處理的數據
    - Footer: `DLE ETX`
  - **計算校驗和**：`calculate_checksum()` 計算 XOR 校驗和
  - **完整封包**：`Header + Payload + Footer + CKS`

### 6. 封包發送層 (`packet/center.py` + `config/network.py`)
- **發送封包**：`PacketCenter.send_command()` 發送指令
  - 記錄序列號到 `pending_seqs`（用於追蹤 ACK 回應）
  - 獲取目標地址（從配置中讀取 TC IP 和 Port）
  - `PacketCenter.send()` 記錄發送日誌（地址、描述、封包內容）
  - `network.send_data()` 通過 UDP socket 發送到目標地址

### 7. ACK 追蹤 (`packet/center.py`)
- **接收 ACK**：接收線程收到 ACK 封包後
  - 解析 ACK 封包，提取序列號
  - 檢查序列號是否在 `pending_seqs` 中
  - 如果在，記錄確認信息並從 `pending_seqs` 移除
  - 完成指令狀態追蹤

### 構建結果
下傳封包包含：
- **封包結構**：`DLE STX SEQ ADDR(2) LEN(2) PAYLOAD DLE ETX CKS`
- **PAYLOAD 內容**：指令碼（2 bytes）+ 字段數據（按定義順序）
- **序列號管理**：自動遞增，線程安全，用於追蹤指令狀態


5F43 79 召喚 0F81

## 待實現
- **Nak**
- **共享接收線程**
- **UDP代理**

## 代處理
- **5FC6**
- **maxgreen**

- **過度抽象 Over Engineering**
- **facade packet_center**


- **FP 轉 OOP**

- **endian:little 解法**