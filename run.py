#!/usr/bin/env python3
"""Todo List 启动入口。"""
from __future__ import annotations

import argparse
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

DEFAULT_PORT = 5050


def _start_server(host: str, port: int) -> None:
    from app import app  # noqa: WPS433

    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


def _wait_for_server(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as resp:
                if resp.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.15)
    return False


def run_desktop(host: str, port: int) -> None:
    """Windows 桌面版：内嵌窗口，不打开系统浏览器。"""
    import webview

    url = f"http://{host}:{port}"
    server = threading.Thread(target=_start_server, args=(host, port), daemon=True)
    server.start()

    if not _wait_for_server(url):
        print(f"[ERROR] 服务启动失败: {url}")
        sys.exit(1)

    webview.create_window(
        "Todo List",
        url,
        width=1200,
        height=800,
        min_size=(900, 600),
        text_select=True,
    )
    webview.start()


def run_browser(host: str, port: int, open_browser: bool) -> None:
    """开发模式：可选打开系统浏览器。"""
    open_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = f"http://{open_host}:{port}"

    if open_browser:
        def _open() -> None:
            time.sleep(1.0)
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()

    print("=" * 44)
    print("  Todo List 正在运行")
    print(f"  浏览器访问: {url}")
    print("  数据保存在程序目录下的 data 文件夹")
    print("  按 Ctrl+C 停止服务")
    print("=" * 44)

    _start_server(host, port)


def main() -> None:
    from paths import is_frozen

    parser = argparse.ArgumentParser(description="Todo List")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，0.0.0.0 允许局域网访问")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true", help="开发模式下不自动打开浏览器")
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="桌面窗口模式（打包 exe 默认启用）",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="强制使用系统浏览器（仅开发调试）",
    )
    args = parser.parse_args()

    use_desktop = (is_frozen() or args.desktop) and not args.browser
    host = "127.0.0.1" if use_desktop else args.host

    if use_desktop:
        run_desktop(host, args.port)
    else:
        run_browser(host, args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
