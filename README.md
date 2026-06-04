# Todo List — 个人事项 & 日历视图

从智枢通达平台独立抽出的轻量事项管理工具。**无需登录**，使用 SQLite 本地存储，Windows 和 Mac 均可运行，解压后启动即可分享使用。

## 功能

| 模块 | 说明 |
|------|------|
| **个人事项** | 创建/编辑/删除待办，支持优先级、状态、周期任务、备注 |
| **日历视图** | 月视图 + 当日/逾期事项，范围切换：我的 / 部门 / 公司 |
| **常规事项** | 日历下方展示长期跟踪的常规事项 |
| **周期任务** | 支持每天/每周/每月/每季度/每年等频率 |

## 谁需要装 Python？

| 角色 | 要不要 Python | 怎么做 |
|------|---------------|--------|
| **最终用户**（同事、朋友） | **不要** | 只收 `TodoList.exe`，双击即用 |
| **你（打包一次）** | 要，或改用下方 GitHub 自动打包 | 生成 exe 后发给所有人 |

对方机器**没有 Python、不会装**完全没问题——前提是你要先准备好 **`TodoList.exe`** 发给他，而不是发整个源码文件夹或 `run.bat`。

```
发给用户的 zip 里只需要：
├── TodoList.exe
└── USER_README.txt（可选）

用户解压 → 双击 TodoList.exe → 完成
```

---

## 打包 exe 的三种方式（任选其一）

### 方式 A：GitHub 自动打包（推荐，本机可没有 Python）

1. 把 `todo_list` 文件夹上传到 GitHub 仓库
2. 打开仓库 **Actions** → 选择 **Build Windows EXE** → **Run workflow**
3. 跑完后在 **Artifacts** 下载 `TodoList-Windows.zip`
4. 解压后把 `TodoList.exe` 发给用户

云端 Windows 环境会自动装好 Python 并完成打包，你不需要在自己电脑上折腾。

### 方式 B：Windows 本机打包

```cmd
cd todo_list
build_exe.bat
```

成功后使用 `dist\TodoList.exe`（约 15~25 MB）。

### 方式 C：找一台已装 Python 的 Windows 电脑

同事/公司电脑只要能跑通 `build_exe.bat`，打包一次即可给全公司用同一个 exe。

> exe 必须在 Windows 环境生成（PyInstaller 不能从 Mac 直接打出 Windows 的 exe）。Mac 上只能打 Mac 版，见 `build_mac.sh`。

---

## 开发者运行（需 Python）

### Mac / Linux

```bash
cd todo_list
chmod +x start.sh
./start.sh
```

### Windows

双击 **`run.bat`**（不要用含中文的旧脚本；`start.bat` 会转调 `run.bat`）。

若已打包，请直接双击 **`dist\TodoList.exe`**，无需 Python。

```cmd
cd todo_list
run.bat
```

启动后浏览器访问：**http://127.0.0.1:5050**

### 局域网分享

服务绑定 `0.0.0.0:5050`，同一局域网内的其他设备可通过 `http://<你的IP>:5050` 访问。

> 注意：无登录意味着同一数据库可被所有访问者读写。适合小范围内网使用；如需隔离请各自维护一份数据目录。

## 目录结构

```
todo_list/
├── app.py              # Flask 主程序
├── db.py               # SQLite 数据库
├── calendar_service.py # 日历与周期展开逻辑
├── data/todo.db        # 数据库文件（首次运行自动创建）
├── templates/          # 页面模板
├── static/             # CSS / JS
├── run.py              # 启动入口（exe 也使用此文件）
├── paths.py            # 打包路径适配
├── todo_list.spec      # PyInstaller 配置
├── build_exe.bat       # Windows 一键打包 exe
├── build_mac.sh        # Mac 一键打包
├── USER_README.txt     # 随 exe 分发的用户说明
└── requirements.txt
```

## 使用说明

1. **个人事项**：创建事项，按范围（我的/部门/公司）筛选。
2. **日历视图**：切换范围后查看月历，点击日期查看当日与逾期事项。
4. **数据备份**：复制 `data/todo.db` 即可备份全部数据。

## 与智枢通达的差异

| 项目 | 智枢通达 | Todo List |
|------|---------|-----------|
| 数据库 | MySQL | SQLite |
| 登录 | 需要 | 不需要 |
| 用户体系 | portal_users | 文本字段（姓名） |
| AI 工作历程总结 | 有 | 无（可后续扩展） |
| HubChat / 督办 | 有 | 无 |

## 手动安装（可选）

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py --port 5050
```

## 许可证

MIT
