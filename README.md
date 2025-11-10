# 交通控制系统 - 数据驱动设计版本

## 项目结构

```
traffic_control_dd/
├── config/              # 配置模块
│   ├── config.py        # 配置管理
│   └── constants.py     # 常量定义
├── core/                # 核心功能模块
│   ├── frame.py         # 帧编解码
│   ├── checksum.py      # 校验和计算
│   └── utils.py         # 工具函数
├── packet/              # 封包处理模块（核心）
│   ├── definitions/     # 封包定义（数据驱动核心）
│   ├── parser/          # 解析器
│   ├── builder/         # 构建器
│   ├── processor/       # 处理器
│   └── registry.py      # 注册中心
├── network/             # 网络通信模块
│   ├── udp_transport.py # UDP传输层
│   └── buffer.py        # 缓冲区管理
├── logging/             # 日志模块
│   └── setup.py         # 日志配置
└── main.py              # 主程序入口
```

## 设计特点

1. **数据驱动设计**：封包格式定义与解析逻辑分离
2. **模块化架构**：职责清晰，易于维护
3. **易于扩展**：添加新封包类型只需添加定义
4. **类型安全**：定义清晰，减少错误

## 使用方法

```python
from packet import PacketRegistry

# 获取注册中心
registry = PacketRegistry()

# 解析封包
packet = registry.parse(frame_bytes)

# 构建封包
frame = registry.build("5F10", {
    "control_strategy": 1,
    "effect_time": 60
}, seq=1, addr=3)

# 处理封包
registry.process(packet)
```

## 运行

```bash
python main.py
```

## 支持的封包类型

- 5F03: 時相資料維管理
- 5F0C: 時相步階變換控制管理
- 5FC0: 控制策略回報
- 5F00: 主動回報
- 5FC8: 時制計畫回報
- 5F08: 現場操作回報
- 5FC6: 一般日時段型態查詢回報
- 0F80: 設定回報（有效）
- 0F81: 設定/查詢回報（無效）
- 0F04: 系統狀態回報
- 0FC0: 查詢現場設備編號回報
- 0F02: 回報終端設備現場手動更改時間

