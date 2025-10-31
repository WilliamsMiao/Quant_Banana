# 部署指南

本文档介绍如何在服务器上部署量化交易系统。

## 快速开始

### 一键部署

```bash
# 克隆项目（如果还没有）
git clone <your-repo-url>
cd Quant_Banana

# 运行部署脚本
./scripts/deploy.sh
```

### 分步部署

#### 1. 环境检查

```bash
./scripts/deploy.sh --check-only
```

这会检查：
- Python版本（需要 >= 3.9）
- pip是否安装
- 其他必要工具

#### 2. 只安装依赖

```bash
./scripts/deploy.sh --install-deps
```

这会：
- 创建虚拟环境
- 安装所有依赖包
- 验证关键依赖

#### 3. 创建systemd服务（可选）

```bash
# 创建服务文件
./scripts/deploy.sh --create-service

# 安装并启动服务（需要sudo权限）
sudo cp /tmp/quant-trading.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable quant-trading
sudo systemctl start quant-trading

# 查看服务状态
sudo systemctl status quant-trading

# 查看日志
sudo journalctl -u quant-trading -f
```

## 配置

### 1. 配置文件

部署脚本会自动从示例文件创建配置文件（如果不存在）：

- `config/settings/base.yaml` - 主配置文件
- `config/secrets/secrets.yaml` - 密钥配置（需要手动填写）

### 2. 必须配置的密钥

编辑 `config/secrets/secrets.yaml`，至少需要配置：

```yaml
secrets:
  futu:
    ws_key: "your_futu_ws_key"
  
  deepseek:
    api_key: "your_deepseek_api_key"
  
  dingding:
    webhook: "https://oapi.dingtalk.com/robot/send?access_token=..."
    secret: "your_dingtalk_secret"
  
  dingding_tuning:
    webhook: "https://oapi.dingtalk.com/robot/send?access_token=..."
    secret: "your_dingtalk_secret"
```

### 3. 市场数据配置

在 `config/settings/base.yaml` 中配置：

```yaml
market_data:
  primary_provider: "futu"  # 主数据源
  subscription:
    symbols: ["HK.00700"]  # 订阅的股票代码
    period: "1m"            # K线周期
```

## 启动系统

### 方式1: 直接运行

```bash
./run.sh
```

### 方式2: 后台运行

```bash
nohup ./run.sh > logs/output.log 2>&1 &
```

### 方式3: 使用systemd服务

```bash
# 启动
sudo systemctl start quant-trading

# 停止
sudo systemctl stop quant-trading

# 重启
sudo systemctl restart quant-trading

# 查看状态
sudo systemctl status quant-trading

# 查看日志
sudo journalctl -u quant-trading -f
```

## 目录结构

部署后，项目目录结构如下：

```
Quant_Banana/
├── .venv/                    # Python虚拟环境
├── backend/                  # 后端代码
├── config/
│   ├── settings/
│   │   └── base.yaml         # 主配置文件
│   └── secrets/
│       └── secrets.yaml      # 密钥配置（需手动填写）
├── data/
│   ├── trade_journal/        # 交易记录
│   └── signal_performance/   # 信号性能数据
├── logs/                     # 日志文件
├── run.sh                    # 启动脚本
└── scripts/
    └── deploy.sh            # 部署脚本
```

## 验证部署

### 1. 检查依赖

```bash
source .venv/bin/activate
python -c "import futu; print('Futu SDK OK')"
python -c "import pandas; print('Pandas OK')"
```

### 2. 测试配置

```bash
python -c "
from backend.main_runner import load_config
cfg = load_config()
print('配置加载成功')
print('数据源:', cfg.get('market_data', {}).get('primary_provider'))
"
```

### 3. 测试Futu连接

确保Futu OpenD在运行：

```bash
# 检查Futu OpenD是否运行
# 应该在 127.0.0.1:11111 监听
netstat -an | grep 11111
```

## 常见问题

### 1. 虚拟环境问题

如果虚拟环境有问题，删除重建：

```bash
rm -rf .venv
./scripts/deploy.sh --install-deps
```

### 2. 依赖安装失败

某些依赖可能需要系统库支持：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip build-essential

# CentOS/RHEL
sudo yum install -y python3-devel gcc gcc-c++
```

### 3. Futu SDK安装失败

手动安装：

```bash
source .venv/bin/activate
pip install futu-api
```

### 4. 权限问题

确保有写入权限：

```bash
chmod -R 755 data logs config/secrets
```

### 5. 端口占用

如果Futu OpenD端口被占用：

```bash
# 检查端口占用
netstat -tuln | grep 11111
lsof -i :11111
```

## 维护

### 更新代码

```bash
git pull
source .venv/bin/activate
pip install -r requirements/base.txt --upgrade
```

### 查看日志

```bash
# 应用日志
tail -f logs/app.log

# 如果使用systemd
sudo journalctl -u quant-trading -f

# 实时输出
tail -f logs/output.log
```

### 停止服务

```bash
# 如果直接运行，Ctrl+C

# 如果后台运行
pkill -f "python.*main_runner"

# 如果使用systemd
sudo systemctl stop quant-trading
```

## 安全建议

1. **保护密钥文件**
   - `config/secrets/secrets.yaml` 包含敏感信息
   - 确保文件权限：`chmod 600 config/secrets/secrets.yaml`
   - 不要提交到Git

2. **防火墙配置**
   - 只开放必要端口
   - Futu OpenD使用本地端口（127.0.0.1）

3. **日志轮转**
   - 配置日志轮转避免日志文件过大
   - 使用logrotate或systemd的日志管理

## 性能优化

1. **虚拟环境优化**
   - 使用SSD存储
   - 足够的磁盘空间（至少1GB）

2. **系统资源**
   - 建议至少2GB RAM
   - CPU: 2核或以上

3. **网络**
   - 稳定的网络连接（访问API需要）
   - 低延迟（交易决策需要）

## 监控

建议监控以下指标：

- 系统资源使用（CPU、内存、磁盘）
- 网络连接状态
- Futu OpenD连接状态
- API调用成功率
- 交易执行成功率
- 日志错误率

可以使用以下工具：

- `htop` - CPU和内存监控
- `journalctl` - systemd日志
- `tail -f logs/app.log` - 应用日志

