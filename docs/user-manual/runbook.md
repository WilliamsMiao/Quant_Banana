## 运行流程与调参指南（Runbook）

本项目已移除前端面板，采用 Futu OpenD → 策略层 → AI 决策 → 钉钉推送 的链路。本文档覆盖组件架构、配置、启动步骤、参数说明与排障。

### 一、组件架构
- 数据获取层（Futu OpenD）
  - `backend/api_clients/futu_client/client.py`：封装 OpenQuoteContext、K 线订阅与拉取。
  - `backend/data/market_data/futu_provider.py`：对外提供标准 `Bar` 数据，负责订阅、拉取、标准化。
- 缓存层
  - `backend/data/cache/market_cache.py`：内存环形缓存，保存最近 N 根 Bar。
- 策略层（事件驱动）
  - `backend/core/event_engine/event_manager.py`：事件总线。
  - `backend/core/trading_engine/strategy_runner.py`：周期拉取数据→转 DataFrame→调用策略→发事件。
  - `backend/strategies/strategy_library/technical/intraday_vwap_reversion.py`：日内 VWAP 偏离反转策略。
- AI 决策层
  - `backend/ai/{api_manager.py,prompt_manager.py,ai_gateway.py,decision_engine.py}`：DeepSeek 接入、Prompt 模版、事件消费与决策产出（SYSTEM_EVENT: AI_DECISION）。
- 推送层
  - `backend/utils/dingtalk_bot.py`：钉钉机器人 Markdown 推送（含签名）。
- 运行入口
  - `backend/main_runner.py`：装配各组件、加载配置、启动事件循环。

### 二、配置
所有通用配置在 `config/settings/base.yaml`；密钥类在 `config/secrets/api-keys.yaml`。

1) Futu OpenD
```yaml
api:
  futu:
    host: "127.0.0.1"
    api_port: 11111
    ws_port: 33333
    ws_key: "<your_ws_key>"
```

2) 订阅标的与周期（Futu 代码）
```yaml
market_data:
  subscription:
    symbols: ["HK.00700", "US.AAPL"]
    period: "1m"       # 支持：1m/3m/5m/15m/30m/60m/1d
```

3) DeepSeek
```yaml
api:
  deepseek:
    base_url: "https://api.deepseek.com"

# config/secrets/api-keys.yaml
deepseek:
  api_key: "<your_api_key>"
```

4) 钉钉机器人
```yaml
dingding:
  webhook: "<your_webhook>"
  secret: "<your_secret>"
```

### 三、启动
1) 安装依赖（需本机可安装 futu-api）
```bash
pip install -r requirements/base.txt
pip install futu-api
```

2) 启动 OpenD（确保与 `api.futu.*` 一致，有分钟K权限）

3) 运行入口
```bash
python backend/main_runner.py
```

可选：一次性触发策略信号（用于验证 AI/钉钉链路）
```bash
TEST_EMIT_SIGNAL=1 python backend/main_runner.py
```

### 四、关键参数与调优
- 订阅周期 `market_data.subscription.period`
  - 映射至 Futu KLType（1m→K_1M 等）。分钟级有自然的 1 分钟刷新节奏。

- Runner 调度（`backend/core/trading_engine/strategy_runner.py`）
  - `pull_interval_sec`：默认 2s，每次循环的拉取与评估频率；可适度加大以降噪与节流。
  - `lookback`：默认 200，用于构建 DataFrame 与指标计算的历史长度。

- 策略参数（`intraday_vwap_reversion.py`）
  - `deviation`：价格相对 VWAP 偏离阈值（默认 0.005=0.5%）。调小更容易触发、调大更保守。
  - `min_volume`：当根 Bar 的最小成交量门槛。

- AI 层
  - Prompt 模板定义于 `backend/main_runner.py` 中 `PromptManager.register("ai_decision", ...)`。可根据风格/审慎程度调整措辞。
  - DeepSeek 模型与参数：目前在 `backend/api_clients/deepseek_client/client.py` 默认 `model="deepseek-chat"`，可扩展温度/最大 tokens。

- 推送
  - 钉钉推送默认包含：策略动作、模型输出、原始市场数据尾部（最近 10 条）与总条数统计。

### 五、日志与可观测性
- Runner 周期日志：打印每标的最近一根 K 线 `close` 与计算出的 `VWAP`。
- 事件：`MARKET_DATA`（市场）、`STRATEGY_SIGNAL`（策略）、`SYSTEM_EVENT(type=AI_DECISION)`（AI 决策）。
- 错误：
  - OpenD 连接失败 ECONNREFUSED → 确认 OpenD 进程、端口、权限。
  - 获取 K 线前需订阅 → 由 Provider 在 `subscribe()` 自动调用订阅，若仍报错，确认权限与标的编码。
  - DeepSeek 403/401 → 确认 `api-keys.yaml`、网络访问与剩余额度。

### 六、常见问题（FAQ）
1) 为什么没看到策略信号？
   - 使用分钟K时，每分钟才会有新数据；策略需满足偏离阈值与成交量门槛。
   - 可调小 `deviation`、增大 `lookback` 或选择波动更大的标的验证。

2) 如何新增策略？
   - 参考 `intraday_vwap_reversion.py`，继承 `BaseStrategy` 并实现 `generate_signals()` 与 `calculate_position_size()`；在 `main_runner.py` 中替换实例。

3) 如何接其他数据源？
   - 实现 `backend/data/market_data/interfaces.py` 中的 `MarketDataProvider` 协议（connect/subscribe/fetch_bars/close），并在 `main_runner.py` 注入替换。

4) 如何推送更多原始数据？
   - 当前默认推送最近 10 条 `Bar` 的 JSON 预览（总条数在标题中标注）。可在 `backend/main_runner.py` 的 `print_ai_decision()` 中调整截断数量与格式。

### 七、运维建议
- 将 OpenD 运行与本服务解耦（独立进程/服务），并做启动前健康检查。
- 为 `TEST_EMIT_SIGNAL` 提供命令行开关或管理脚本，避免误用于生产。
- 对钉钉推送做节流与去重（可基于信号哈希与窗口）。

---
如需更细致的指标与风控（滑点、成交模拟、仓位与风限约束、订单路由），建议在 Runner 与策略层之间增加风控中间件，并完善 `OrderManager` 的实盘网关适配。



