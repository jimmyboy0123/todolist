# Todo List — 个人事项 & 日历视图

轻量事项管理工具。**无需登录**，使用 SQLite 本地存储，Windows 和 Mac 均可运行。

## 功能

| 模块 | 说明 |
|------|------|
| **个人事项** | 创建/编辑/删除待办，支持优先级、状态、周期任务、备注、附件 |
| **日历视图** | 月视图 + 当日/逾期事项，范围切换：我的 / 部门 / 公司 |
| **常规事项** | 日历下方展示长期跟踪的常规事项 |
| **周期任务** | 支持每天/每周/每月/每季度/每年等频率 |

## Windows 打包 exe（无需本机 Python）

### 方式 A：GitHub Actions（推荐）

1. 将代码推送到 GitHub 的 `main` 分支
2. 打开仓库 **Actions** → **Build Windows EXE**
3. 等待运行完成，在 **Artifacts** 下载 `TodoList-Windows.zip`
4. 解压后双击 `TodoList.exe` 即可使用

也可在 Actions 页点击 **Run workflow** 手动触发打包。

### 方式 B：Windows 本机打包

```cmd
build_exe.bat
```

成功后使用 `dist\TodoList.exe`。

---

## 快速启动（开发）

### Mac / Linux

```bash
cd todo_list
chmod +x start.sh
./start.sh
```

### Windows

双击 **`run.bat`**（或 `start.bat`，效果相同）。

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
├── data/               # 数据库与附件（首次运行自动创建）
├── templates/          # 页面模板
├── static/             # CSS / JS
├── run.py              # 启动入口
├── start.sh / run.bat  # 一键启动脚本
├── todo_list.spec      # PyInstaller 配置
├── build_exe.bat       # Windows 本机打包
├── .github/workflows/build-windows.yml  # GitHub 自动打包
└── requirements.txt
```

## 使用说明

1. **个人事项**：创建事项，按范围（我的/部门/公司）筛选。
2. **日历视图**：切换范围后查看月历，点击日期查看当日与逾期事项。
3. **数据备份**：复制 `data/` 文件夹即可备份数据库与附件。

## 手动安装（可选）

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py --host 0.0.0.0 --port 5050
```

## 与智枢通达的差异

| 项目 | 智枢通达 | Todo List |
|------|---------|-----------|
| 数据库 | MySQL | SQLite |
| 登录 | 需要 | 不需要 |
| 用户体系 | portal_users | 文本字段（姓名） |
| AI 工作历程总结 | 有 | 无（可后续扩展） |
| HubChat / 督办 | 有 | 无 |

## 许可证

MIT
