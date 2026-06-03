# 系统架构

## 目录

- [概述](#概述)
- [技术栈](#技术栈)
- [分层结构](#分层结构)
- [请求数据流](#请求数据流)
- [目录结构](#目录结构)
- [Legacy 与 v2 关系](#legacy-与-v2-关系)

## 概述

Youzi v2 是物流运营工具的新版 Web 应用：Vue 3 前端 + FastAPI 后端 + SQLite 本地数据库。从仓库根目录 Legacy 单页应用逐步迁移功能，当前已落地运单管理、船期监控、海运预警、客户/渠道管理等模块。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3、Vite、TypeScript、Tailwind CSS 4、Naive UI、Pinia |
| 后端 | Python 3、FastAPI、Uvicorn、Pydantic |
| 数据库 | SQLite（单文件，`youzi_v2/data/`） |
| 配置 | 仓库根 `config/config.json`（gitignore，承运商密钥等） |

## 分层结构

```text
┌─────────────────────────────────────────┐
│  frontend/          Vue SPA（端口 5173）   │
│  src/views、components、api、types       │
└──────────────────┬──────────────────────┘
                   │ HTTP /api → Vite 代理
┌──────────────────▼──────────────────────┐
│  app.py             FastAPI 路由层       │
│  schemas/           请求/响应模型        │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  services/          业务逻辑             │
│  轨迹同步、Excel 导入、承运商对接等       │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  db/                仓储 + 表定义        │
│  *_table.py、*_repository.py            │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  data/youzi.db      SQLite               │
└─────────────────────────────────────────┘
```

## 请求数据流

以「运单列表查询」为例：

1. 用户打开 `/shipments` → `ShipmentsView.vue` 挂载
2. 前端调用 `GET /api/v1/shipments`（`src/api/shipments.ts`）
3. Vite 将 `/api` 代理到 `http://127.0.0.1:3001`
4. `app.py` 解析查询参数，调用 `shipments_repository`
5. Repository 执行 SQL，返回 Pydantic 模型 JSON
6. 前端渲染表格、筛选器、轨迹抽屉等

后台定时任务（轨迹同步）由 `services/tracking_sync_scheduler.py` 在 Uvicorn 启动时注册，不经过 HTTP。

## 目录结构

```text
youzi_v2/
├── app.py                 # FastAPI 主入口 + Legacy Jinja 页面
├── frontend/              # Vue SPA
├── backend/app/           # 可选 ASGI 封装（未来拆分）
├── db/                    # SQLite 表 + Repository
├── services/              # 业务服务
├── schemas/               # Pydantic 模型
├── config/                # Excel 列映射等非密钥配置
├── templates/、static/    # Legacy 后台静态资源
├── scripts/               # 命令行脚本（轨迹同步等）
├── tests/                 # pytest
├── docs/                  # 详细文档（本目录）
└── data/                  # 本地数据库（gitignore）
```

## Legacy 与 v2 关系

- **唯一活跃代码库**：`youzi_v2/`（见 `.cursor/rules/youzi-v2-only.mdc`）
- 仓库根 `index.html`、`js/`、`server/` 等为 Legacy，只读参考，新功能不写回 Legacy
- `app.py` 同时服务 Legacy Jinja 页面（`/`、`/tools/product-import`）与新 API
- 生产构建可选：前端 `npm run build` 后由后端单端口托管（见 [deployment.md](./deployment.md)）

## 相关文档

- [database.md](./database.md) — 表结构
- [api.md](./api.md) — API 索引
- [deployment.md](./deployment.md) — 部署与环境变量
