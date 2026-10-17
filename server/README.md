# youzi 本地服务（Node + SQLite）

为前端提供 API，把报价历史、计算历史存到 SQLite，替代 localStorage。

## 安装与运行

```bash
cd server
npm install
npm start
```

浏览器访问：**http://localhost:3000**（页面和接口同源，无需 CORS 跨域）。

静态服务仅开放首页、`js/`、`css/`、`img/`、`font/` 以及页面引用的公开数据脚本和 `config/style.js`。
本地配置、数据库、日志、`data/private_data.js` 不通过静态服务提供；地址数据由现有后端接口加载。

安全回归测试：在 `server/` 执行 `npm test`，覆盖静态文件访问边界与报价历史 HTML 注入。

## 接口说明

- **报价历史**
  - `GET /api/quote-history` — 返回全部，按时间倒序，最多 100 条
  - `POST /api/quote-history` — 新增一条，body 为整条记录（含 id、timestamp 等）
  - `DELETE /api/quote-history/:id` — 按 id 删除一条
  - `DELETE /api/quote-history` — 清空

- **计算历史**
  - `GET /api/calculation-history` — 返回全部，按时间倒序，最多 50 条
  - `POST /api/calculation-history` — 新增一条，body 为 { id, timestamp, data, summary, details }
  - `DELETE /api/calculation-history/:id` — 按 id 删除一条
  - `DELETE /api/calculation-history` — 清空

数据库文件：`server/youzi.db`（首次请求时自动建表）。

## 前端迁移

前端目前仍使用 localStorage。要切到本服务：

1. 用 `http://localhost:3000` 打开页面（通过本服务访问，不要直接打开 file://）。
2. 在 `js/logistics.js`、`js/common.js` 中把对 `quoteHistory`、`calculationHistory` 的 localStorage 读写改为对上述接口的 `fetch` 调用（可按你之前的「逐步迁移」顺序改）。

滞销分页条数（`staleShipmentsPageSize`）仍建议保留在 localStorage，不必入库。
