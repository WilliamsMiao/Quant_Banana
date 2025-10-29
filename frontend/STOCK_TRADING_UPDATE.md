# 股票交易系统更新说明

## ✅ 已完成的更新

### 1. 数据源调整
- **加密货币 → 股票**：将价格显示组件从加密货币改为股票
- **股票列表**：AAPL、MSFT、GOOGL、TSLA、NVDA、AMZN
- **实时数据**：支持股票价格和涨跌幅的实时更新

### 2. API服务层
- **股票服务** (`stockService.js`)：获取股票价格、历史数据
- **交易服务** (`tradingService.js`)：账户信息、持仓、订单管理
- **策略服务** (`strategyService.js`)：AI策略管理
- **回测服务** (`backtestService.js`)：回测数据获取
- **WebSocket服务** (`websocketService.js`)：实时数据推送

### 3. 模型数据更新
- **策略类型**：AI驱动多因子选股、价值投资、技术分析等
- **策略描述**：每个AI模型都有对应的股票交易策略
- **性能指标**：显示账户价值和收益率变化

### 4. 实时数据连接
- **WebSocket订阅**：股票价格、账户价值、订单更新
- **自动重连**：连接断开时自动重连
- **数据同步**：实时更新前端显示

### 5. 图表数据源
- **后端数据**：从回测服务获取真实数据
- **实时更新**：WebSocket推送更新图表
- **时间过滤**：支持ALL和72H时间范围

### 6. UI文本本地化
- **中文界面**：主要文本改为中文
- **股票术语**：使用股票交易相关术语
- **策略描述**：详细说明每个AI策略

## 🔧 技术架构

### 前端服务层
```
services/
├── api.js              # HTTP客户端配置
├── stockService.js     # 股票数据服务
├── tradingService.js   # 交易服务
├── strategyService.js  # 策略服务
├── backtestService.js  # 回测服务
└── websocketService.js # WebSocket服务
```

### 数据流
```
后端API → 前端服务层 → Vue组件 → 用户界面
    ↓
WebSocket → 实时更新 → 自动刷新
```

## 📊 数据接口

### 股票价格API
```javascript
// 获取股票价格列表
GET /api/market-data/stocks
Response: [
  {
    symbol: "AAPL",
    price: 150.25,
    change: 1.25,
    icon: "/stocks/aapl.svg"
  }
]

// WebSocket实时更新
{
  type: "market_data",
  symbol: "AAPL",
  price: 150.30,
  change: 1.30
}
```

### 策略数据API
```javascript
// 获取策略列表
GET /api/strategies
Response: [
  {
    id: 1,
    name: "DeepSeek Chat V3.1",
    strategy: "AI驱动多因子选股",
    value: 186305.01,
    change: 86.33
  }
]
```

## 🚀 使用方法

### 1. 环境配置
```bash
# 复制环境变量文件
cp .env.example .env

# 编辑配置
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### 2. 启动开发服务器
```bash
cd frontend
npm install
npm run dev
```

### 3. 后端服务要求
- 后端API服务运行在 `http://localhost:8000`
- WebSocket服务运行在 `ws://localhost:8000/ws`
- 支持CORS跨域请求

## 📝 注意事项

1. **数据依赖**：前端现在完全依赖后端API提供数据
2. **实时更新**：需要后端支持WebSocket实时数据推送
3. **错误处理**：API调用失败时会显示模拟数据
4. **资源文件**：需要添加股票图标到 `public/stocks/` 目录

## 🔄 下一步计划

1. 连接真实的后端API
2. 添加更多股票数据源
3. 实现策略详情页面
4. 添加交易历史查看功能
5. 优化移动端显示

所有更新已完成，前端现在完全适配股票交易场景！
