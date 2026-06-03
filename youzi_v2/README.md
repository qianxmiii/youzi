# Youzi v2

Vue 3 + Tailwind + FastAPI 物流运营工具（Linear / Vercel 风格），从仓库根 Legacy 单页应用逐步迁移功能。

## 目录

- [项目介绍](#项目介绍)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [安装部署](#安装部署)
- [环境变量](#环境变量)
- [数据库概览](#数据库概览)
- [模块列表](#模块列表)
- [API 文档入口](#api-文档入口)
- [开发规范](#开发规范)
- [更新记录](#更新记录)
- [私密配置](#私密配置)

## 项目介绍

Youzi 面向跨境物流日常运营：运单监控、轨迹同步、船期挂靠、海运预警、客户/渠道与地址簿管理。v2 采用前后端分离架构，新功能仅在 `youzi_v2/` 开发（Legacy 目录只读参考）。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3、Vite、TypeScript、Tailwind CSS 4、Naive UI |
| 后端 | Python、FastAPI、Uvicorn、Pydantic |
| 数据库 | SQLite（`youzi_v2/data/`） |
| 配置 | 根目录 `config/config.json`（gitignore） |

## 系统架构

```text
frontend (5173)  ──/api──►  app.py (3001)  ──►  services  ──►  db  ──►  SQLite
```

详细说明：[docs/architecture.md](./docs/architecture.md)

## 安装部署

本地开发需 **两个终端**，均在 **仓库根目录**执行。

### 1. 后端 API（端口 3001）

```bash
pip install -r youzi_v2/requirements.txt
uvicorn youzi_v2.app:app --host 0.0.0.0 --port 3001 --reload
```

### 2. 前端（端口 5173）

**Windows PowerShell**（若 `npm` 报「禁止运行脚本」，改用 `npm.cmd`）：

```powershell
cd youzi_v2/frontend
npm.cmd install
npm.cmd run dev
```

**macOS / Linux / Git Bash**：

```bash
cd youzi_v2/frontend
npm install
npm run dev
```

### 访问地址

| 服务 | URL |
|------|-----|
| 新前端（Vue） | http://localhost:5173 |
| 后端 API / Legacy 后台 | http://localhost:3001/ |

前端通过 Vite 将 `/api` 代理到 `http://127.0.0.1:3001`。局域网访问：后端 `--host 0.0.0.0`，前端已配置 `host: true`。

生产构建与更多部署细节：[docs/deployment.md](./docs/deployment.md)

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `YOUZI_DB_PATH` | SQLite 路径 | `youzi_v2/data/youzi.db` |
| `YOUZI_TRACKING_SYNC_INTERVAL_HOURS` | 轨迹同步间隔（小时）；`0` 关闭 | `2` |
| `YOUZI_TRACKING_SYNC_INITIAL_DELAY_SEC` | 启动后首次同步延迟（秒） | `60` |

## 数据库概览

SQLite 单文件，表在启动时自动初始化。核心表：`shipments`、`vessel_voyages`、`voyage_port_calls`、轨迹日志表、客户/渠道/地址簿等。

完整表结构：[docs/database.md](./docs/database.md)

## 模块列表

| 模块 | 路径 | 说明 | 文档 |
|------|------|------|------|
| 前端 | `frontend/` | Vue SPA、页面与组件 | [frontend/README.md](./frontend/README.md) |
| 后端 | `app.py`、`backend/` | FastAPI 路由 | [backend/README.md](./backend/README.md) |
| 数据层 | `db/` | 表定义与 Repository | [db/README.md](./db/README.md) |
| 业务服务 | `services/` | 轨迹、Excel、承运商 | [services/README.md](./services/README.md) |
| 模型 | `schemas/` | Pydantic 请求/响应 | [schemas/README.md](./schemas/README.md) |
| 运单域 | 跨模块 | 运单 CRUD、轨迹、异常 | [docs/modules/shipment/](./docs/modules/shipment/README.md) |
| 船期域 | 跨模块 | 航次、挂靠、预警 | [docs/modules/vessel-schedule/](./docs/modules/vessel-schedule/README.md) |

### 前端路由迁移状态

| 路由 | 状态 | 旧代码 |
|------|------|--------|
| `/` | ✅ 工作台 | — |
| `/shipments` | ✅ 运单管理 | `stales.html` |
| `/vessel-schedules` | ✅ 船期监控 | — |
| `/addresses` | ✅ 地址簿 | `/api/addresses` |
| `/statistics` | ✅ 统计 | — |
| `/customers`、`/channels` | ✅ | — |
| `/scheduled-tasks` | ✅ 计划任务 | — |
| `/admin` | ✅ 码表 | `templates/admin.html` |
| `/box`、`/quote`、`/cost`、`/library` | 待迁 | Legacy JS |

## API 文档入口

- 完整索引：[docs/api.md](./docs/api.md)
- 运单流程：[docs/shipment-flow.md](./docs/shipment-flow.md)
- 仓库地址：[docs/warehouse-flow.md](./docs/warehouse-flow.md)

常用示例：

```bash
curl http://127.0.0.1:3001/api/v1/health
curl "http://127.0.0.1:3001/api/v1/shipments?page=1&page_size=20"
curl -X POST "http://127.0.0.1:3001/api/v1/shipments/import" -F "file=@运单数据.xlsx"
curl -O "http://127.0.0.1:3001/api/v1/vessel-schedules/template"
```

## 开发规范

1. **仅改 `youzi_v2/`** — Legacy 根目录不写新功能（见 `.cursor/rules/youzi-v2-only.mdc`）
2. **文档同步** — 改代码必须更新相关 README、`docs/`、`CHANGELOG.md`（见 `.cursor/rules/youzi-v2-docs.mdc`）
3. **密钥** — 只放 `config/config.json`，禁止提交 Git
4. **日志** — 运行日志写 `youzi_v2/logs/`，勿提交
5. **测试** — `pytest youzi_v2/tests/`

文档中心：[docs/README.md](./docs/README.md)

## 更新记录

见 [CHANGELOG.md](./CHANGELOG.md)。

## 私密配置

- 私密项写在仓库根 `config/config.json`（勿提交 Git）
- 承运商在 `vendors` 中配置，由 `services/carrier_vendors.py` 读取
- 详见根目录 `config/README.md`

## 目录结构

```text
youzi_v2/
├── frontend/          # Vue 3 + Vite + Tailwind
├── backend/app/       # 可选 ASGI 封装
├── app.py             # FastAPI 主入口
├── db/                # SQLite 仓储
├── services/          # 业务逻辑
├── schemas/           # Pydantic 模型
├── docs/              # 详细文档
├── config/            # Excel 列映射等
├── tests/             # pytest
├── scripts/           # 命令行脚本
├── templates/、static/ # Legacy 后台
├── CHANGELOG.md       # 变更记录
└── data/              # 本地数据库（gitignore）
```
