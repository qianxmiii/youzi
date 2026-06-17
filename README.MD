# Youzi

Youzi 是面向跨境物流运营的内部 Web 工具，覆盖运单管理、轨迹同步、船期监控、海运预警、客户/渠道/地址簿、统计与计划任务等日常工作流。

当前主线应用位于 `youzi_v2/`：前端使用 Vue 3 + Vite + TypeScript，后端使用 FastAPI，数据存储为本地 SQLite。仓库根目录下的旧版静态页、脚本和 `server/` 仍保留作历史功能参考，新功能优先在 `youzi_v2/` 内开发。

## 快速开始

本地开发需要两个终端，命令均从仓库根目录执行。

### 1. 启动后端

```bash
pip install -r youzi_v2/requirements.txt
uvicorn youzi_v2.app:app --host 0.0.0.0 --port 3001 --reload
```

后端启动后可访问：

- FastAPI / Legacy 后台：`http://localhost:3001/`
- 健康检查：`http://localhost:3001/api/v1/health`

### 2. 启动前端

Windows PowerShell：

```powershell
cd youzi_v2/frontend
npm.cmd install
npm.cmd run dev
```

macOS / Linux / Git Bash：

```bash
cd youzi_v2/frontend
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

Vite 已将 `/api` 和 `/legacy` 代理到 `http://127.0.0.1:3001`，局域网访问可直接使用本机 IP 加 `5173` 端口。

## 环境要求

- Python 3.10+，推荐 Python 3.11+
- Node.js 18+
- npm
- Windows 环境建议保留 `tzdata` 依赖，世界时间等功能需要 IANA 时区数据

## 配置与数据

私密配置放在仓库根目录的 `config/config.json`，不要写入业务代码，也不要提交 Git。该文件通常包含内部轨迹服务 `base_url`、承运商 `vendors`、Token、app、authorization、cookie 等配置。

常用环境变量：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `YOUZI_DB_PATH` | SQLite 数据库路径 | `youzi_v2/data/youzi.db` |
| `YOUZI_TRACKING_SYNC_INTERVAL_HOURS` | 后台轨迹同步间隔，设为 `0` 可关闭 | `2` |
| `YOUZI_TRACKING_SYNC_INITIAL_DELAY_SEC` | 服务启动后首次同步延迟秒数 | `60` |

SQLite 表会在后端启动时按需初始化。本地数据库、日志和构建产物不应提交。

## 主要功能

- 工作台概览：运单、海运预警、ETA 提醒、订阅消息与世界时间
- 运单管理：导入/导出、查询筛选、批量编辑、异常开启/关闭、轨迹抽屉、订阅通知
- 轨迹同步：内部轨迹、承运商轨迹、同步日志、新鲜度统计、计划任务
- 船期监控：航次、挂靠港、外部船期抓取、港口/运单到港预警
- 资料中心：地址簿、仓库地址、Excel 导入导出
- 客户与渠道：客户资料、渠道码表、默认渠道种子
- 系统管理：码表、计划任务、世界时间显示设置
- Legacy 工具：商品导入、旧版报价/箱规/资料库等迁移中的页面或脚本

## 目录结构

```text
.
├── youzi_v2/                 # 当前主线应用
│   ├── app.py                # FastAPI 主入口，包含 API 与部分 Legacy 页面
│   ├── frontend/             # Vue 3 + Vite + TypeScript 前端
│   ├── db/                   # SQLite 表定义与 Repository
│   ├── services/             # 轨迹、船期、Excel、计划任务等业务服务
│   ├── schemas/              # Pydantic 请求/响应模型
│   ├── docs/                 # 架构、数据库、API、部署和模块文档
│   ├── tests/                # pytest 测试
│   ├── scripts/              # 命令行同步/排查脚本
│   ├── templates/            # 后端渲染页面
│   └── static/               # 后端静态资源
├── config/                   # 本地私密配置说明与 config.json 放置目录
├── css/ js/ data/ img/       # Legacy 单页应用资源
├── server/                   # Legacy Node/Express 服务
├── tools/                    # 辅助工具，如商品导入转换
├── index.html                # Legacy 入口
├── stales.html               # Legacy 运单/滞留相关页面
└── report.html               # Legacy 报表页面
```

## 常用命令

后端测试：

```bash
pytest youzi_v2/tests/
```

前端类型检查：

```bash
cd youzi_v2/frontend
npm run typecheck
```

前端构建：

```bash
cd youzi_v2/frontend
npm run build
```

手动执行全量轨迹同步：

```bash
python youzi_v2/scripts/sync_all_tracking_scheduled.py
```

## 文档入口

- `youzi_v2/README.md`：v2 应用总览
- `youzi_v2/docs/architecture.md`：系统架构
- `youzi_v2/docs/database.md`：数据库结构
- `youzi_v2/docs/api.md`：API 索引
- `youzi_v2/docs/deployment.md`：部署与运行
- `youzi_v2/docs/modules/shipment/README.md`：运单模块
- `youzi_v2/docs/modules/vessel-schedule/README.md`：船期模块
- `config/README.md`：本地私密配置说明

## 开发约定

1. 新功能优先写入 `youzi_v2/`，Legacy 目录用于参考和渐进迁移。
2. 改动 API、数据表、导入模板或关键业务流程时，同步更新相关 README、`docs/` 与 `CHANGELOG.md`。
3. Token、Cookie、Authorization、AppKey 等敏感信息只能放在本地 `config/config.json`。
4. 日志、数据库、临时文件、构建产物和 `node_modules/` 不提交。
5. 提交前至少运行与改动相关的后端测试或前端类型检查。

## Legacy 说明

根目录旧版页面仍可能被业务使用，但不再作为新功能主入口：

- `index.html`：旧版工具集合入口
- `stales.html`：旧版运单/滞留相关页面
- `report.html`：旧版报表页面
- `channelAPI.py`、`work.py`、`check_stale_shipments.py`：历史脚本与数据处理入口
- `server/`：旧版 Express 服务

迁移功能时，优先复用旧版业务规则和数据口径，但实现应落在 `youzi_v2/` 的前后端、服务层和测试中。
