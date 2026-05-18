# Youzi v2

Vue 3 + Tailwind + FastAPI 新壳（Linear / Vercel 风格），从仓库根目录 `index.html` 逐步迁移功能。

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

## 开发（推荐）

**终端 1 — API（仓库根目录）**

```bash
pip install -r youzi_v2/requirements.txt
uvicorn youzi_v2.app:app --host 0.0.0.0 --port 3001 --reload
```

**终端 2 — 新前端**

```bash
cd youzi_v2/frontend
npm install
npm run dev
```

浏览器打开：**http://localhost:5173**（或终端里 Vite 打印的 `Network: http://192.168.x.x:5173`）

- 新 UI：工作台、侧栏路由（占位页标「待迁」）
- API：`/api` 代理到 `3001`（报价历史、地址簿等仍走现有接口）
- Legacy 后台：http://localhost:3001/ （Jinja admin）

**只能用 localhost？** 若后端用了 `--host 127.0.0.1`，或 Vite 未开 `host: true`，手机/别的电脑无法用局域网 IP 打开。请用上面的 `0.0.0.0` + 本仓库已配置的 Vite `host: true`。

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

表头需与 `config/shipment_excel_columns.json` 一致（运单号、客户订单号、用户名、件数…）。
