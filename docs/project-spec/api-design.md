# API设计文档

## API概览

本系统提供RESTful API和WebSocket API，支持以下功能：

- 用户认证和授权
- 交易操作（下单、撤单、查询）
- 策略管理（创建、编辑、运行）
- 回测分析
- 实时数据推送
- 系统监控

## 认证机制

- **JWT Token**: 用于API认证
- **API Key**: 用于第三方集成
- **OAuth 2.0**: 支持第三方登录

## 核心API端点

### 交易相关
- `POST /api/trading/orders` - 创建订单
- `GET /api/trading/orders` - 查询订单
- `DELETE /api/trading/orders/{id}` - 撤销订单
- `GET /api/trading/positions` - 查询持仓

### 策略相关
- `GET /api/strategies` - 获取策略列表
- `POST /api/strategies` - 创建策略
- `PUT /api/strategies/{id}` - 更新策略
- `POST /api/strategies/{id}/start` - 启动策略

### 回测相关
- `POST /api/backtesting/run` - 运行回测
- `GET /api/backtesting/results/{id}` - 获取回测结果
- `GET /api/backtesting/performance/{id}` - 获取性能指标

## WebSocket事件

- `market_data` - 实时行情数据
- `order_update` - 订单状态更新
- `strategy_signal` - 策略信号
- `system_alert` - 系统告警
