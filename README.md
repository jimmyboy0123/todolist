# Todo List — 个人事项 & 日历视图

轻量事项管理工具。**无需登录**，使用 SQLite 本地存储。

- **Windows**：桌面程序 + 安装包（独立窗口，不打开浏览器）
- **Mac / 开发**：可用脚本在浏览器中运行

## 功能

| 模块 | 说明 |
|------|------|
| **个人事项** | 创建/编辑/删除待办，支持优先级、状态、周期任务、备注、附件 |
| **日历视图** | 月视图 + 当日/逾期事项，范围切换：我的 / 部门 / 公司 |
| **常规事项** | 日历下方展示长期跟踪的常规事项 |
| **周期任务** | 支持每天/每周/每月/每季度/每年等频率 |

## Windows 桌面版（给最终用户）

从 GitHub Actions 下载两种产物之一：

| 产物 | 说明 |
|------|------|
| **TodoList-Setup** | 安装程序，推荐普通用户：安装到「开始菜单」、可创建桌面快捷方式 |
| **TodoList-Portable** | 绿色版：解压后双击 `TodoList.exe`，无需安装 |

### 获取安装包

1. 推送代码到 GitHub `main` 分支
2. 打开 **Actions** → **Build Windows Desktop**
3. 构建完成后在 **Artifacts** 下载 `TodoList-Setup` 或 `TodoList-Portable`

安装/启动后会出现 **Todo List 桌面窗口**，不会自动打开 Chrome/Edge 浏览器标签页。

### 本机打包（需 Windows + Python）

```cmd
build_exe.bat
```

生成 `dist\TodoList.exe`。若已安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)，可再执行：

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\TodoList.iss
```

得到 `installer\output\TodoList-Setup.exe`。

---

## 快速启动（开发 / Mac）

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
├── installer/TodoList.iss  # Inno Setup 安装包脚本
├── .github/workflows/build-windows.yml  # GitHub 自动打包桌面版
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
