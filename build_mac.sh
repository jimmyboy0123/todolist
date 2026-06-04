#!/usr/bin/env bash
# Mac 本地应用打包（生成 dist/TodoList 可执行文件）
set -e
cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
  echo "错误: 需要 Python 3.10+"
  exit 1
fi

python3 -m venv .venv_build
source .venv_build/bin/activate
pip install -q -r requirements.txt pyinstaller

echo "正在打包 Mac 版..."
python3 -m PyInstaller todo_list.spec --clean -y

if [ -f dist/TodoList ]; then
  cp USER_README.txt dist/ 2>/dev/null || true
  echo ""
  echo "打包成功: dist/TodoList"
  echo "运行: ./dist/TodoList"
else
  echo "打包失败"
  exit 1
fi
