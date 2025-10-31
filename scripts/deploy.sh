#!/bin/bash
# 一键部署脚本 - 量化交易系统
# 用法: ./scripts/deploy.sh [选项]
#   选项:
#     --install-deps   只安装依赖，不启动服务
#     --create-service 创建systemd服务文件
#     --check-only     只检查环境，不安装

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 默认选项
INSTALL_DEPS_ONLY=false
CREATE_SERVICE=false
CHECK_ONLY=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-deps)
            INSTALL_DEPS_ONLY=true
            shift
            ;;
        --create-service)
            CREATE_SERVICE=true
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            echo "用法: $0 [--install-deps] [--create-service] [--check-only]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   量化交易系统 - 一键部署脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ============ 环境检查 ============
echo -e "${YELLOW}[1/7] 检查环境...${NC}"

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}❌ Python版本过低: $PYTHON_VERSION (需要 >= 3.9)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python版本: $PYTHON_VERSION${NC}"

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip3 未安装，尝试安装...${NC}"
    python3 -m ensurepip --upgrade || {
        echo -e "${RED}❌ 无法安装pip3${NC}"
        exit 1
    }
fi

echo -e "${GREEN}✅ pip3 已安装${NC}"

# 如果只是检查，则退出
if [ "$CHECK_ONLY" = true ]; then
    echo -e "${GREEN}✅ 环境检查完成${NC}"
    exit 0
fi

# ============ 创建必要目录 ============
echo ""
echo -e "${YELLOW}[2/7] 创建必要目录...${NC}"

DIRS=(
    "data"
    "data/trade_journal"
    "data/signal_performance"
    "logs"
    "config/secrets"
)

for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}✅ 创建目录: $dir${NC}"
    else
        echo -e "${BLUE}ℹ️  目录已存在: $dir${NC}"
    fi
done

# ============ 检查配置文件 ============
echo ""
echo -e "${YELLOW}[3/7] 检查配置文件...${NC}"

# 检查base.yaml
if [ ! -f "config/settings/base.yaml" ]; then
    if [ -f "config/settings/base.yaml.example" ]; then
        echo -e "${YELLOW}⚠️  base.yaml 不存在，从 base.yaml.example 创建...${NC}"
        cp "config/settings/base.yaml.example" "config/settings/base.yaml"
        echo -e "${YELLOW}⚠️  请编辑 config/settings/base.yaml 并配置你的设置${NC}"
    else
        echo -e "${RED}❌ 配置文件不存在: config/settings/base.yaml${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ config/settings/base.yaml 已存在${NC}"
fi

# 检查secrets.yaml
if [ ! -f "config/secrets/secrets.yaml" ]; then
    if [ -f "config/secrets/secrets.yaml.example" ]; then
        echo -e "${YELLOW}⚠️  secrets.yaml 不存在，从 secrets.yaml.example 创建...${NC}"
        cp "config/secrets/secrets.yaml.example" "config/secrets/secrets.yaml"
        echo -e "${RED}⚠️  请编辑 config/secrets/secrets.yaml 并配置你的密钥和API密钥${NC}"
        echo -e "${RED}⚠️  重要：确保配置了 Futu OpenD、DeepSeek、DingTalk 等必要的密钥${NC}"
    else
        echo -e "${YELLOW}⚠️  secrets.yaml 不存在，请手动创建${NC}"
        touch "config/secrets/secrets.yaml"
        echo -e "${RED}⚠️  请编辑 config/secrets/secrets.yaml 并配置你的密钥${NC}"
    fi
else
    echo -e "${GREEN}✅ config/secrets/secrets.yaml 已存在${NC}"
fi

# ============ 创建虚拟环境 ============
echo ""
echo -e "${YELLOW}[4/7] 设置虚拟环境...${NC}"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✅ 虚拟环境已创建${NC}"
else
    echo -e "${BLUE}ℹ️  虚拟环境已存在${NC}"
fi

# 激活虚拟环境
source .venv/bin/activate

# 升级pip
echo -e "${YELLOW}升级pip...${NC}"
pip install --upgrade pip -q || {
    echo -e "${RED}❌ pip升级失败${NC}"
    exit 1
}

# ============ 安装依赖 ============
echo ""
echo -e "${YELLOW}[5/7] 安装依赖包...${NC}"

if [ -f "requirements/base.txt" ]; then
    echo -e "${YELLOW}安装基础依赖...${NC}"
    pip install -r requirements/base.txt -q || {
        echo -e "${RED}❌ 依赖安装失败${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${RED}❌ requirements/base.txt 不存在${NC}"
    exit 1
fi

# 验证关键依赖
echo -e "${YELLOW}验证关键依赖...${NC}"
REQUIRED_PACKAGES=("pandas" "numpy" "yaml" "requests")

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    # 处理特殊的包名映射
    import_name="${pkg//-/_}"
    if [ "$pkg" = "yaml" ]; then
        import_name="yaml"
    fi
    if python -c "import ${import_name}" 2>/dev/null; then
        echo -e "${GREEN}✅ $pkg${NC}"
    else
        echo -e "${YELLOW}⚠️  $pkg 导入失败，可能需要手动安装${NC}"
    fi
done

# ============ 验证Futu SDK ============
echo ""
echo -e "${YELLOW}[6/7] 验证Futu SDK...${NC}"

if python -c "from futu import OpenQuoteContext" 2>/dev/null; then
    echo -e "${GREEN}✅ Futu SDK 已安装${NC}"
else
    echo -e "${YELLOW}⚠️  Futu SDK 未正确安装，尝试重新安装...${NC}"
    pip install futu-api -q || {
        echo -e "${YELLOW}⚠️  从requirements安装失败，尝试单独安装...${NC}"
        pip install futu-api --no-cache-dir
    }
    if python -c "from futu import OpenQuoteContext" 2>/dev/null; then
        echo -e "${GREEN}✅ Futu SDK 安装成功${NC}"
    else
        echo -e "${YELLOW}⚠️  Futu SDK 安装可能失败，但继续部署...${NC}"
        echo -e "${YELLOW}   可以在部署后手动运行: pip install futu-api${NC}"
    fi
fi

# 检查Futu OpenD是否运行（如果可能）
if command -v netstat &> /dev/null || command -v ss &> /dev/null; then
    if (netstat -an 2>/dev/null | grep -q ":11111") || (ss -an 2>/dev/null | grep -q ":11111"); then
        echo -e "${GREEN}✅ Futu OpenD 端口11111 正在监听${NC}"
    else
        echo -e "${YELLOW}⚠️  Futu OpenD 可能未运行（端口11111未监听）${NC}"
        echo -e "${YELLOW}   请确保Futu OpenD已启动${NC}"
    fi
fi

# 如果只安装依赖，则退出
if [ "$INSTALL_DEPS_ONLY" = true ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
fi

# ============ 创建启动脚本 ============
echo ""
echo -e "${YELLOW}[7/7] 创建启动脚本...${NC}"

# 创建run.sh启动脚本
cat > run.sh << 'EOFSCRIPT'
#!/bin/bash
# 量化交易系统启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行 ./scripts/deploy.sh"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查配置文件
if [ ! -f "config/secrets/secrets.yaml" ]; then
    echo "⚠️  警告: config/secrets/secrets.yaml 不存在"
    echo "   请配置必要的API密钥"
fi

# 检查交易时间（如果Python可用）
if command -v python3 &> /dev/null; then
    python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')
try:
    from backend.utils.trading_hours import TradingHoursManager
    import yaml
    
    # 加载配置
    with open("config/settings/base.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    
    trading_hours_cfg = cfg.get("trading_hours", {})
    market = trading_hours_cfg.get("market", "HK")
    timezone = trading_hours_cfg.get("timezone", "Asia/Hong_Kong")
    enable_holiday_check = trading_hours_cfg.get("enable_holiday_check", True)
    
    hours_manager = TradingHoursManager(market=market, timezone=timezone, enable_holiday_check=enable_holiday_check)
    now = hours_manager._get_now()
    
    if hours_manager.is_trading_time(now):
        print(f"✅ 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"✅ 当前在交易时间内，可以启动服务")
    elif hours_manager.is_trading_day(now):
        next_open = hours_manager.get_open_time_today()
        if next_open:
            print(f"⚠️  当前时间: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"⚠️  当前不在交易时间内")
            print(f"   今日开盘时间: {next_open.strftime('%H:%M:%S')}")
        else:
            close_time = hours_manager.get_close_time_today()
            if close_time:
                print(f"⚠️  今日已收盘: {close_time.strftime('%H:%M:%S')}")
    else:
        next_open = hours_manager.get_next_open_time()
        print(f"⚠️  当前时间: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"⚠️  当前不是交易日（可能是周末或节假日）")
        print(f"   下次开盘时间: {next_open.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("")
        print("   服务将在非交易时间自动退出")
except Exception as e:
    # 如果检查失败，不阻止启动，只是不显示提示
    pass
PYEOF
    echo ""
fi

# 运行主程序
echo "🚀 启动量化交易系统..."
python backend/main_runner.py "$@"
EOFSCRIPT

chmod +x run.sh
echo -e "${GREEN}✅ 启动脚本已创建: ./run.sh${NC}"

# 创建systemd服务文件（如果请求）
if [ "$CREATE_SERVICE" = true ]; then
    echo ""
    echo -e "${YELLOW}创建systemd服务文件...${NC}"
    
    SERVICE_NAME="quant-trading"
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    
    # 获取当前用户
    CURRENT_USER=$(whoami)
    
    cat > /tmp/${SERVICE_NAME}.service << EOF
[Unit]
Description=Quant Trading System
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${PROJECT_ROOT}
ExecStart=${PROJECT_ROOT}/.venv/bin/python ${PROJECT_ROOT}/backend/main_runner.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    echo -e "${BLUE}服务文件内容:${NC}"
    cat /tmp/${SERVICE_NAME}.service
    echo ""
    echo -e "${YELLOW}要安装systemd服务，请运行:${NC}"
    echo -e "${BLUE}  sudo cp /tmp/${SERVICE_NAME}.service ${SERVICE_FILE}${NC}"
    echo -e "${BLUE}  sudo systemctl daemon-reload${NC}"
    echo -e "${BLUE}  sudo systemctl enable ${SERVICE_NAME}${NC}"
    echo -e "${BLUE}  sudo systemctl start ${SERVICE_NAME}${NC}"
    echo ""
    echo -e "${YELLOW}查看日志:${NC}"
    echo -e "${BLUE}  sudo journalctl -u ${SERVICE_NAME} -f${NC}"
fi

# ============ 部署完成 ============
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}下一步操作:${NC}"
echo ""
echo -e "1. ${YELLOW}配置密钥${NC}"
echo -e "   编辑 config/secrets/secrets.yaml"
echo -e "   确保配置了所有必要的API密钥"
echo ""
echo -e "2. ${YELLOW}配置设置${NC}"
echo -e "   编辑 config/settings/base.yaml"
echo -e "   调整交易策略参数、数据源等"
echo ""
echo -e "3. ${YELLOW}启动系统${NC}"
echo -e "   ${GREEN}./run.sh${NC}"
echo -e "   或使用systemd服务（如果已创建）"
echo ""
echo -e "4. ${YELLOW}查看日志${NC}"
echo -e "   tail -f logs/app.log"
echo -e "   或在项目根目录查看实时输出"
echo ""
echo -e "${BLUE}重要提示:${NC}"
echo -e "  • 确保Futu OpenD已在运行（127.0.0.1:11111）"
echo -e "  • 确保网络连接正常，可以访问DeepSeek API"
echo -e "  • 建议先测试运行，确认配置正确后再长期运行"
echo ""

