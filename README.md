# 量化交易机器人项目 🚀

一个基于Webull、富途和DeepSeek的智能量化交易系统。

## 📁 项目结构

```
quant-trading-bot/
├── 📚 docs/                           # 项目文档
├── 🔧 config/                         # 配置文件
├── 📊 backend/                        # 后端核心
├── 📈 research/                       # 策略研究
├── 🧪 tests/                          # 测试代码
├── 🚀 scripts/                        # 部署和工具脚本
├── 📦 shared/                         # 共享代码
└── 📋 requirements/                   # 依赖管理
```

## 🚀 快速开始

1. 克隆项目
```bash
git clone git@github.com:WilliamsMiao/Quant_Banana.git
cd Quant_Banana
```

2. 安装后端依赖
```bash
pip install -r requirements/base.txt
```

3. 启动开发环境
```bash
# 后端
python backend/web_api/main.py
```

## 🎯 核心功能

- 🤖 **多券商支持**: Webull、富途API集成
- 🧠 **AI驱动**: DeepSeek大模型策略生成
- 📊 **实时交易**: 事件驱动交易引擎
- 🔍 **智能研究**: RAG知识库系统
- 📈 **完整回测**: 多维度回测分析
- 🛡️ **风险控制**: 实时风险监控

## 🏗️ 技术栈

### 后端
- **框架**: FastAPI + WebSocket
- **数据**: Pandas + NumPy + SQLAlchemy
- **AI**: DeepSeek API + ChromaDB
- **缓存**: Redis
- **监控**: Prometheus + Grafana


## 📝 开发规范

- **分支策略**: Git Flow
- **提交规范**: Conventional Commits
- **代码质量**: Black + isort + flake8
- **测试覆盖**: pytest + coverage

## 📄 许可证

MIT License
