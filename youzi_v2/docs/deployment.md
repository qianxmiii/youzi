# 部署指南

## 目录

- [环境要求](#环境要求)
- [本地开发](#本地开发)
- [环境变量](#环境变量)
- [生产构建](#生产构建)
- [定时任务](#定时任务)
- [私密配置](#私密配置)
- [日志](#日志)

## 环境要求

- Python 3.10+（推荐 3.11+）
- Node.js 18+（前端）
- 仓库根目录可访问 `config/config.json`（承运商密钥，本地自行创建）

## 本地开发

在**仓库根目录**开两个终端。

### 后端（端口 3001）

```bash
pip install -r youzi_v2/requirements.txt
uvicorn youzi_v2.app:app --host 0.0.0.0 --port 3001 --reload
```

### 前端（端口 5173）

**Windows PowerShell**（若 `npm` 报脚本策略错误，用 `npm.cmd`）：

```powershell
cd youzi_v2/frontend
npm.cmd install
npm.cmd run dev
```

**macOS / Linux**：

```bash
cd youzi_v2/frontend
npm install
npm run dev
```

| 服务 | URL |
|------|-----|
| Vue 前端 | http://localhost:5173 |
| FastAPI / Legacy | http://localhost:3001 |

前端 Vite 将 `/api` 代理到 `http://127.0.0.1:3001`。

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `YOUZI_DB_PATH` | SQLite 文件路径 | `youzi_v2/data/youzi.db` |
| `YOUZI_TRACKING_SYNC_INTERVAL_HOURS` | 轨迹同步间隔（小时）；`0` 关闭 | `2` |
| `YOUZI_TRACKING_SYNC_INITIAL_DELAY_SEC` | 启动后首次同步延迟（秒） | `60` |

示例（PowerShell）：

```powershell
$env:YOUZI_TRACKING_SYNC_INTERVAL_HOURS = "4"
uvicorn youzi_v2.app:app --host 0.0.0.0 --port 3001 --reload
```

## 生产构建

```bash
cd youzi_v2/frontend && npm run build
cd ../..
uvicorn youzi_v2.app:app --host 0.0.0.0 --port 3001
```

当前生产仍以 Legacy 根路径 `/` 为主；SPA 可独立部署或后续改为 `backend` 托管 `frontend/dist`。

## 定时任务

Uvicorn 启动后默认开启后台轨迹同步（内部 + 承运商，仅 `IN_TRANSIT` 运单）。

不依赖后端常驻时，可用系统计划任务：

```bash
# 仓库根目录
python youzi_v2/scripts/sync_all_tracking_scheduled.py
```

或通过前端「计划任务」页 / API 手动触发（见 [api.md](./api.md)）。

## 私密配置

**禁止**将 Token、appKey、authorization 等写入 `youzi_v2/` 业务代码或提交 Git。

- 路径：仓库根 `config/config.json`（gitignore）
- 承运商：`vendors` 数组，由 `services/carrier_vendors.py` 按 `platform` 读取
- 说明：根目录 `config/README.md`

## 日志

轨迹同步日志：`youzi_v2/logs/tracking-sync-YYYY-MM-DD.log`（gitignore，勿提交）。

排查：本地打开日志文件或查看后端控制台输出。

## 相关文档

- [architecture.md](./architecture.md)
- [../README.md](../README.md)
