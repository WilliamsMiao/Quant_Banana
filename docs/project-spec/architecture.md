# 系统架构设计

## 整体架构

本量化交易系统采用微服务架构，包含以下核心组件：

- **前端应用**: Vue 3 + Vite 构建的现代化Web界面
- **后端API**: FastAPI + WebSocket 提供RESTful API和实时通信
- **交易引擎**: 事件驱动的交易执行引擎
- **数据层**: 多数据源集成和缓存系统
- **AI模块**: DeepSeek大模型集成和RAG知识库
- **监控系统**: 实时监控和告警

## 技术选型

### 后端技术栈
- **Web框架**: FastAPI
- **数据库**: PostgreSQL + Redis
- **消息队列**: RabbitMQ
- **AI集成**: DeepSeek API + ChromaDB
- **监控**: Prometheus + Grafana

### 前端技术栈
- **框架**: Vue 3 + Composition API
- **构建工具**: Vite
- **状态管理**: Pinia
- **UI组件**: Element Plus
- **图表库**: ECharts

## 部署架构

- **容器化**: Docker + Docker Compose
- **负载均衡**: Nginx
- **CI/CD**: GitHub Actions
- **云平台**: 支持AWS/Azure/GCP
