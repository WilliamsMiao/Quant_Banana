# 量化交易机器人项目 🚀

一个基于富途OpenD和DeepSeek AI的智能量化交易系统，支持实时市场数据订阅、策略信号生成、AI决策融合和自动化交易执行。

## ✨ 核心特性

### 🤖 AI驱动的交易决策
- **DeepSeek大模型集成**: 利用AI进行市场分析和交易决策
- **智能信号融合**: 策略引擎信号与AI决策智能融合，确保最优执行
- **动态权重调整**: 基于历史表现自动调整策略和AI的权重分配
- **性能跟踪系统**: 完整记录每个信号源的交易结果，持续优化决策质量

### 📊 多信号融合引擎
- **方向一致性增强**: 当策略和AI方向一致时，自动提升置信度和仓位
- **冲突智能解决**: 基于加权得分和历史表现解决信号冲突
- **保守观望机制**: 严重冲突时选择观望，避免不必要风险
- **多层质量过滤**: 置信度、风险收益比、仓位控制、冷却期管理

### 📈 优化的香港股票日内策略
- **动态资本配置**: 根据账户资金自动调整策略参数
- **智能频率优化**: 基于交易成本和市场波动动态调整交易频率
- **多时间框架分析**: 结合多周期技术指标增强信号质量
- **精确成本控制**: 考虑佣金、印花税等实际交易成本

### 🔔 实时通知与监控
- **DingTalk机器人集成**: 实时推送交易决策和执行结果
- **完整的决策记录**: 记录AI的完整思考过程和决策依据
- **信号冲突日志**: 追踪策略与AI的方向分歧，便于分析优化

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone git@github.com:WilliamsMiao/Quant_Banana.git
cd Quant_Banana
```

### 2. 安装依赖
```bash
pip install -r requirements/base.txt
```

### 3. 配置敏感信息

复制配置文件模板并填入真实信息：

```bash
# 复制基础配置模板
cp config/settings/base.yaml.example config/settings/base.yaml

# 复制敏感信息模板
cp config/secrets/secrets.yaml.example config/secrets/secrets.yaml
```

编辑 `config/secrets/secrets.yaml`，填入：
- Futu OpenD WebSocket密钥
- DingTalk机器人webhook和secret
- 数据库密码（如需要）

⚠️ **重要**: `config/secrets/secrets.yaml` 文件包含敏感信息，不会被提交到Git。

### 4. 配置交易参数

编辑 `config/settings/base.yaml`：

```yaml
market_data:
  subscription:
    symbols: ["HK.00700"]  # 要交易的标的
    period: "1m"           # K线周期

strategy:
  optimized_hk_intraday:
    enabled: true
    initial_capital: 100000  # 初始资金（会自动从账户读取）
    signal_strength_threshold: 60
    risk_reward_ratio: 1.5
    max_position_ratio: 0.3

signal_fusion:
  source_weights:
    strategy: 0.45    # 策略引擎权重
    ai: 0.55          # AI决策权重
  min_confidence: 60  # 最小置信度阈值（%）
  min_risk_reward: 1.3
  cooldown_period_minutes: 10
  enable_performance_tracking: true
```

### 5. 启动服务

确保富途OpenD已运行，然后：

```bash
python backend/main_runner.py
```

服务将：
- 连接到富途OpenD订阅市场数据
- 运行策略生成交易信号
- 调用DeepSeek AI进行决策分析
- 融合策略和AI信号生成最终决策
- 执行交易并推送通知

### 6. 查看日志

```bash
# 主运行日志
tail -f /tmp/quant_trading.log

# DeepSeek原始响应
tail -f logs/deepseek_responses.jsonl

# 信号冲突记录
tail -f logs/signal_conflicts.jsonl

# 性能跟踪数据
cat data/signal_performance.json
```

## 📁 项目结构

```
Quant_Banana/
├── 📚 backend/                      # 后端核心代码
│   ├── ai/                          # AI决策引擎
│   │   ├── decision_engine.py       # AI决策核心逻辑
│   │   ├── trade_memory.py          # 交易记忆系统
│   │   └── prompt_manager.py        # AI提示词管理
│   ├── core/trading_engine/
│   │   ├── signal_fusion.py         # 🆕 信号融合引擎
│   │   └── strategy_runner.py       # 策略运行器
│   ├── strategies/                  # 交易策略
│   │   └── strategy_library/
│   │       └── technical/
│   │           └── optimized_hk_intraday.py  # 优化的HK日内策略
│   ├── api_clients/                 # API客户端
│   │   ├── futu_client/             # 富途OpenD客户端
│   │   └── deepseek_client/        # DeepSeek API客户端
│   └── main_runner.py               # 主运行入口
├── 🔧 config/                       # 配置文件
│   ├── settings/
│   │   ├── base.yaml                # 主配置文件（不含敏感信息）
│   │   └── base.yaml.example        # 配置模板
│   └── secrets/
│       ├── secrets.yaml             # 敏感信息（不提交Git）
│       └── secrets.yaml.example     # 敏感信息模板
├── 📊 data/                         # 数据文件（不提交Git）
│   ├── signal_performance.json      # 信号源性能数据
│   └── trade_journal.jsonl          # 交易记录
├── 📝 logs/                         # 日志文件（不提交Git）
│   ├── deepseek_responses.jsonl     # DeepSeek原始响应
│   └── signal_conflicts.jsonl       # 信号冲突记录
└── 📋 requirements/                 # 依赖管理
    └── base.txt                     # 基础依赖
```

## 🎯 核心功能详解

### 信号融合系统

系统实现了多层次的信号融合机制：

1. **策略信号生成**: 技术指标策略生成初始交易信号
2. **AI决策分析**: DeepSeek AI基于市场数据和技术指标进行深度分析
3. **信号融合**: 
   - 方向一致 → 增强信号（提升置信度，增加仓位）
   - 方向冲突 → 基于历史表现选择胜出方，降低置信度和仓位
   - 严重冲突 → 保守观望（HOLD）
4. **质量过滤**: 通过置信度、风险收益比、仓位控制、冷却期等多层过滤
5. **性能跟踪**: 记录每次交易结果，动态调整信号源权重

### AI决策流程

1. **输入数据**: 
   - 策略信号（方向、原因）
   - 市场数据（K线、当前价、VWAP）
   - 技术指标（关键价位、信号强度、波动率）
   - 账户信息（资金、持仓）
   - 历史反思和长期记忆

2. **AI分析**: DeepSeek自主判断交易方向（buy/sell/hold）

3. **输出结果**:
   - 操作方向、置信度、仓位权重
   - 止损价、止盈价
   - 详细决策依据

### 性能跟踪与权重调整

- **自动记录**: 每次交易执行后自动记录策略和AI的表现
- **成功 rate跟踪**: 跟踪每个信号源的成功率（最近50次交易）
- **权重更新**: 每30分钟基于近期表现自动更新权重
- **数据持久化**: 性能数据保存到 `data/signal_performance.json`

## 🛡️ 安全配置

### 敏感信息管理

所有敏感信息存储在 `config/secrets/secrets.yaml` 中，该文件：
- ✅ 已配置在 `.gitignore` 中，不会提交到Git
- ✅ 包含Futu API密钥、DingTalk配置、数据库密码等

配置文件的加载顺序：
1. 先加载 `config/settings/base.yaml`（基础配置）
2. 再加载 `config/secrets/secrets.yaml`（敏感信息）
3. 合并到统一的配置对象

### Git安全

- ✅ `config/secrets/` 目录被忽略（除了 `*.example` 文件）
- ✅ `data/` 和 `logs/` 目录被忽略
- ✅ 敏感信息已从Git历史中清理

## 📊 监控与调试

### 日志文件

- `/tmp/quant_trading.log`: 主运行日志
- `logs/deepseek_responses.jsonl`: DeepSeek的完整响应
- `logs/signal_conflicts.jsonl`: 策略与AI的方向冲突记录
- `data/signal_performance.json`: 信号源性能统计数据

### 关键日志关键字

```bash
# 查看信号融合信息
grep "信号融合\|融合类型\|direction_match" /tmp/quant_trading.log

# 查看性能跟踪
grep "性能跟踪\|权重更新" /tmp/quant_trading.log

# 查看AI决策
grep "AI_DECISION\|决策引擎" /tmp/quant_trading.log
```

## 🏗️ 技术栈

### 后端
- **Python 3.8+**: 核心语言
- **Futu OpenD**: 富途交易API和行情数据
- **DeepSeek API**: AI决策引擎
- **Pandas + NumPy**: 数据处理和计算
- **PyYAML**: 配置文件管理

### 架构特点
- **事件驱动**: 基于事件引擎的异步架构
- **模块化设计**: 清晰的模块分离，易于扩展
- **配置驱动**: 关键参数外部化配置
- **可观测性**: 完整的日志和性能跟踪

## 📝 开发规范

- **分支策略**: Git Flow
- **提交规范**: Conventional Commits
- **代码质量**: 遵循PEP 8规范
- **类型提示**: 使用Python类型注解

## 🔄 更新日志

### v1.1.0 (最新)
- ✨ 新增多信号融合引擎，智能融合策略和AI信号
- ✨ 新增性能跟踪系统，自动调整信号源权重
- ✨ 优化的香港股票日内策略，支持动态资本配置
- 🔒 敏感信息管理优化，从Git历史中清理密钥
- 📊 增强的日志记录和监控能力

### v1.0.0
- 🎉 初始版本发布
- 基础交易功能
- AI决策集成
- DingTalk通知

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📧 联系方式

如有问题，请通过GitHub Issues联系。
