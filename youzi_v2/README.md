# Youzi v2

Vue 3 + Tailwind + FastAPI 新壳（Linear / Vercel 风格），从仓库根目录 `index.html` 逐步迁移功能。

## 启动

本地开发需 **两个终端**，均在 **仓库根目录**（含 `youzi_v2/` 的那一层）执行。

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

前端通过 Vite 将 `/api` 代理到 `http://127.0.0.1:3001`。需局域网访问时，后端使用 `--host 0.0.0.0`，前端已配置 `host: true`，可用终端打印的 `Network: http://192.168.x.x:5173`。

## 结构

```text
youzi_v2/
├── frontend/          # Vue 3 + Vite + Tailwind 4 + Naive UI
├── backend/app/       # 统一 ASGI 入口（可选）
├── app.py             # 现有 API + Legacy Jinja 后台
├── db/                # SQLite 仓储
├── templates/         # Legacy 后台页面
└── data/              # 本地数据库（gitignore）
```

## 生产构建（单端口，可选）

```bash
cd youzi_v2/frontend && npm run build
cd ../..   # 仓库根
uvicorn youzi_v2.app:app --host 0.0.0.0 --port 3001
```

当前生产仍以 Legacy 根路径 `/` 为主；SPA 独立部署或后续改为 `backend` 托管 `frontend/dist`。

## 迁移清单

| 路由 | 状态 | 旧代码 |
|------|------|--------|
| `/` | ✅ 壳 | — |
| `/box` | 待迁 | `logistics.js` calculate |
| `/quote` | 待迁 | `updateQuote` |
| `/quote/batch` | 待迁 | `generateBatchQuote` |
| `/cost` | 待迁 | `tab.js` DDU/DDP |
| `/library` | 待迁 | 术语 / 书签 / 备忘录 |
| `/addresses` | 待迁 | `/api/addresses` |
| `/shipments` | 待迁 | `stales.html` |
| `/admin` | 待迁 | `templates/admin.html` |

## API

| 路径 | 说明 |
|------|------|
| `GET /api/v1/health` | 新前端健康检查 |
| `GET /api/health` | 兼容旧版 |
| `/api/quote-history*` | 报价历史 |
| `/api/addresses*` | 地址簿 |
| `/api/product-import*` | 箱单转换 |
| `/api/v1/shipments*` | 运单 CRUD + Excel 导入 |

### 运单 Excel 导入

```bash
curl -X POST "http://127.0.0.1:3001/api/v1/shipments/import" \
  -F "file=@运单数据.xlsx"
```

表头需与 `config/shipment_excel_columns.json` 一致（运单号、客户订单号、货件号、用户名、件数…）。

### 轨迹定时同步（每 2 小时）

后端 `uvicorn` 启动后默认开启后台任务：**每 2 小时**全量同步 **内部轨迹 + 承运商轨迹**（仅 `IN_TRANSIT` 转运中运单，与页面手动同步一致）。日志写入 `youzi_v2/logs/tracking-sync-YYYY-MM-DD.log`。

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| `YOUZI_TRACKING_SYNC_INTERVAL_HOURS` | 间隔（小时）；`0` 关闭 | `2` |
| `YOUZI_TRACKING_SYNC_INITIAL_DELAY_SEC` | 启动后首次执行延迟（秒） | `60` |

不依赖后端常驻时，可用系统计划任务每 2 小时执行一次：

```bash
# 仓库根目录
python youzi_v2/scripts/sync_all_tracking_scheduled.py
```

仅承运商轨迹的旧脚本：`youzi_v2/scripts/sync_carrier_tracking.py`。
