# -*- mode: python ; coding: utf-8 -*-
# Windows 桌面版打包 — GitHub Actions 或 build_exe.bat

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

webview_hidden = collect_submodules("webview")
webview_datas = collect_data_files("webview")

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("templates", "templates"),
        ("static", "static"),
        *webview_datas,
    ],
    hiddenimports=[
        "app",
        "calendar_service",
        "db",
        "paths",
        "webview",
        *webview_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TodoList",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
