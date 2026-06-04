"""应用路径：兼容开发模式与 PyInstaller 打包后的 exe。"""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_app_dir() -> Path:
    """可写目录：开发时为项目根目录，打包后为 exe 所在目录。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_resource_dir() -> Path:
    """只读资源目录：templates、static 等。"""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def get_data_dir() -> Path:
    """SQLite 数据库目录（与 exe 同级的 data/）。"""
    data = get_app_dir() / "data"
    data.mkdir(parents=True, exist_ok=True)
    return data
