#!/bin/bash
# 使用虚拟环境运行主程序的脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ .venv虚拟环境不存在，正在创建..."
    python3 -m venv .venv
    echo "✅ 虚拟环境已创建"
fi

# 激活虚拟环境并运行
source .venv/bin/activate

# 确保依赖已安装
if ! python -c "import futu" 2>/dev/null; then
    echo "📦 安装依赖..."
    pip install -r requirements/base.txt -q
fi

# 运行主程序
echo "🚀 启动量化交易系统（使用.venv环境）..."
python backend/main_runner.py "$@"

