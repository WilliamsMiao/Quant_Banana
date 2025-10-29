# 环境搭建指南

## 系统要求

- Python 3.9+
- Node.js 16+
- PostgreSQL 13+
- Redis 6+
- Docker (可选)

## 开发环境搭建

### 1. 克隆项目
```bash
git clone git@github.com:WilliamsMiao/Quant_Banana.git
cd Quant_Banana
```

### 2. 后端环境
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements/dev.txt

# 配置环境变量
cp config/secrets/api-keys.yaml.example config/secrets/api-keys.yaml
# 编辑配置文件，填入API密钥
```

### 3. 前端环境
```bash
cd frontend
npm install
```

### 4. 数据库设置
```bash
# 启动PostgreSQL和Redis
docker-compose up -d postgres redis

# 运行数据库迁移
python backend/scripts/migrate.py
```

### 5. 启动开发服务器
```bash
# 后端
python backend/web_api/main.py

# 前端
cd frontend
npm run dev
```

## 开发工具配置

### VS Code推荐插件
- Python
- Vue Language Features (Volar)
- Prettier
- ESLint
- GitLens

### 代码格式化
```bash
# Python
black backend/
isort backend/

# JavaScript/Vue
cd frontend
npm run format
```
