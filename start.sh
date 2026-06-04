#!/usr/bin/env bash
# Todo List 启动脚本 (Mac / Linux)
set -e
cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
  echo "错误: 未找到 python3，请先安装 Python 3.10+"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "首次运行，正在创建虚拟环境..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "=========================================="
echo "  Todo List 已启动"
echo "  本机访问: http://127.0.0.1:5050"
echo "  无需登录，可直接分享给他人使用"
echo "  按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

python run.py --host 0.0.0.0 --port 5050
