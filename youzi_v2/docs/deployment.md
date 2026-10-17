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
- `tzdata`（已写入 `requirements.txt`；Windows 上世界时间等功能依赖 IANA 时区库）
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
- 内部轨迹：`base_url`，由 `services/logistics_tracking.py` 读取
- 运单查询（DPS 销售助理接口）：
  - **`dps_authorization`**（推荐）：根级 DPS Bearer，供 `shipment_queryByPerson`、`shipment_queryByOrder`、`dps_route_status_query`、`dps_data_download` 等共用（仍兼容各块内 `Authorization`）
  - **`shipment_queryByPerson`**：查全部运单（url 内已带 `salesAssistantId`、`status` 等筛选），代码注入 `pageNum`、`transitTimeStart`、`transitTimeEnd`（默认当月）
  - **`shipment_queryByOrder`**：按运单号查，拼接 `odds`（多单空格 → `%20`）+ `pageNum`
  - **`dps_route_status_query`**（明细状态轻量同步必填）：仅含 `url`（完整接口地址）；**url 只写在本文件**，业务代码/文档不得写真实地址
  - **`dps_data_download`**（货箱）：exportBox；**POST** + `?ids=` 单个 waybillId；多票逐票请求后 zip（**`YYYYMMDDHHmmss.zip`**）；**单票**保存名为 DPS 响应 `Content-Disposition` 原名（无则回退 `{运单号}_data.ext`），zip 内仍为 `{运单号}_data.ext`
  - **`dps_mark_download`**（单个唛头）：**POST** + `?id=waybillId&type=2`（`type` 可在块内配置，默认 `2`）；**单票**用 DPS 原名（无则回退 `{运单号}_mark.ext`）
  - **`dps_batchmark_download`**（多个唛头）：**POST**，JSON body 为 waybillId **数组**；多票包名 `{YYYYMMDDHHmmss}.ext`
  - **`dps_packinglist_download`**（箱单发票）：**POST** + URL **`?ids=`** waybillId（多票英文逗号拼接，如 `2109884564244705282,2109884627163459585`，无 body）；单票保存 **`{运单号}_箱单发票.ext`**，多票文件名沿用 DPS 原名
  - 响应 `{ code, msg, total, rows }`，按 `total` 与 `pageSize`（默认 10）自动翻页。见 `services/shipment_query_config.py`
  - **DPS 运单同步批处理**（计划任务页）：从 `shipment_queryByPerson` 拉取并 upsert 至本地 `shipments`；`transitTimeStart` / `transitTimeEnd` 可配置，默认当月；**默认关闭**，约 24 小时执行一次。见 `services/shipment_dps_sync.py`
  - **同步哪些字段**：`youzi_v2/config/shipment_dps_sync_fields.json`（`onInsert` / `onUpdate`）；映射逻辑见 `services/shipment_dps_mapper.py`（`customer_no`←`internalOrderNum`，`ref_shipment_no`←`assOrderNumber`）

```json
"dps_authorization": "Bearer <token>",
"shipment_queryByPerson": {
  "url": "https://.../customPageSalesAssistant?pageSize=10&salesAssistantId=...&status=3"
},
"shipment_queryByOrder": {
  "url": "https://.../customPageSalesAssistant?pageSize=10&orderByColumn=createTime&isAsc=asc"
},
"dps_route_status_query": {
  "url": "<明细状态轨迹接口完整 URL，仅写于此>"
},
"dps_data_download": {
  "url": "<货箱 exportBox URL>",
  "method": "POST"
},
"dps_mark_download": {
  "url": "<单个唛头 URL>",
  "method": "POST",
  "type": "2"
},
"dps_batchmark_download": {
  "url": "<批量唛头 URL>",
  "method": "POST"
},
"dps_packinglist_download": {
  "url": "<箱单发票 URL>",
  "method": "POST"
}
```

明细状态轻量同步：`POST /api/v1/shipments/sync-route-status-from-dps`（可选 `shipmentNos`，空则全部）；批处理 `POST /api/v1/scheduled-tasks/run-dps-route-status-sync`。按运单 `waybill_id` 请求配置 URL 并回写 `route_status`。
- 承运商：`vendors` 数组，由 `services/carrier_vendors.py` 按 `platform` 读取；同一承运商多套系统时可在主 vendor 配置 **`fallbackVendor": "森磊2"`**（或 `fallbackVendors` 数组），主系统无轨迹时按序尝试备用
- 企业微信（可选）：`config.json` → `wecom_webhook`（智能机器人长连接 / Webhook 推送、@ 查运单、测试 API）。**完整说明见 [wecom-aibot.md](./wecom-aibot.md)**；凭证勿提交 Git。

- 说明：根目录 `config/README.md`

## 日志

轨迹同步日志：`youzi_v2/logs/tracking-sync-YYYY-MM-DD.log`（gitignore，勿提交）。

企业微信智能机器人：`youzi_v2/logs/wecom-aibot-YYYY-MM-DD.log`（详见 [wecom-aibot.md](./wecom-aibot.md)，勿提交）。

排查：本地打开日志文件或查看后端控制台输出。

## 相关文档

- [wecom-aibot.md](./wecom-aibot.md)
- [architecture.md](./architecture.md)
- [../README.md](../README.md)
