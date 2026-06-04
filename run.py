#!/usr/bin/env python3
"""Todo List 启动入口。"""
from __future__ import annotations

import argparse
import threading
import time
import webbrowser

DEFAULT_PORT = 5050


def main() -> None:
    parser = argparse.ArgumentParser(description="Todo List")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，0.0.0.0 允许局域网访问")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    from app import app  # noqa: WPS433

    open_host = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
    url = f"http://{open_host}:{args.port}"

    if not args.no_browser:
        def _open_browser() -> None:
            time.sleep(1.0)
            webbrowser.open(url)

        threading.Thread(target=_open_browser, daemon=True).start()

    print("=" * 44)
    print("  Todo List 正在运行")
    print(f"  浏览器访问: {url}")
    print("  数据保存在程序目录下的 data 文件夹")
    print("  关闭本窗口即可停止服务")
    print("=" * 44)

    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
