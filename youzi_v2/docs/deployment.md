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

Uvicorn 启动后默认开启后台轨迹同步（内部 + 承运商，仅**在途**运单：`status_code` 为 `2` / `IN_TRANSIT` 等，**不含**港前 DPS Status 0/01/1/4）。

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
  - **`shipment_queryByPerson`**：查全部/在途运单（url 内已带筛选），代码注入 `pageNum`、`transitTimeStart`、`transitTimeEnd`（默认当月）
  - **`shipment_queryByPerson_pickup`**：提货中（Status 01 等）；**GET**；代码注入 `orderTimeStart` / `orderTimeEnd`（非 transitTime）
  - **`shipment_queryByPerson_warehoused`**：已入仓（Status 1 等）；**GET**；同上 `orderTimeStart` / `orderTimeEnd`
  - 可选块内 `"timeRange": "transit" | "order" | "none"` 覆盖默认（pickup/warehoused 默认 `order`）
  - **`shipment_queryByOrder`**：按运单号查，拼接 `odds`（多单空格 → `%20`）+ `pageNum`
  - **`dps_route_status_query`**（明细状态轻量同步必填）：仅含 `url`（完整接口地址）；**url 只写在本文件**，业务代码/文档不得写真实地址
  - **`dps_data_download`**（货箱）：exportBox；**POST** + `?ids=` 单个 waybillId；**单票**保存为 `{运单号}_data.ext`；**多票**各文件重命名后装入文件夹 `{N}票数据_{YYYYMMDDHHmmss}/`，压缩包名为 **`{N}票数据_{YYYYMMDDHHmmss}.zip`**
  - **`dps_mark_download`**（单个唛头）：**POST** + `?id=waybillId&type=2`（`type` 可在块内配置，默认 `2`）；**单票**用 DPS 原名（无则回退 `{运单号}_mark.ext`）
  - **`dps_batchmark_download`**（多个唛头）：**POST**，JSON body 为 waybillId **数组**；多票包名 `{YYYYMMDDHHmmss}.ext`
  - **`dps_packinglist_download`**（箱单发票）：**POST** + URL **`?ids=`** waybillId（多票英文逗号拼接，如 `2109884564244705282,2109884627163459585`，无 body）；单票保存 **`{运单号}_箱单发票.ext`**，多票文件名沿用 DPS 原名
  - **`dps_warehouseform_download`**（排仓单）：**POST** + URL **`?ids=`** waybillId（多票英文逗号拼接，如 `2099310173320552449,2109884564244705282`，无 body）；**每批最多 50 个 id**，勾选超过 50 票时后端自动分批请求，多批结果打包 zip；单票 **`{运单号}_排仓单.ext`**
  - **进仓单（模板）**：`youzi_v2/config/templates/warehouse_entry_template.xlsx`（可选根配置 **`warehouse_entry_template`** 指向其它 xlsx）；按占位符 `{日期}` `{收货仓}` `{收货地址}` `{运单号}` `{合计件数}` 等填充勾选运单；收货地址来自 **`dps_warehouse`**；文件名 **`{N}票进仓单_{YYYYMMDD}.xlsx`**（不依赖 DPS 下载）
  - **进仓单（PDF）**：与 Excel 下载 **同一份临时 xlsx**（同一模板填充），再转为 PDF，版式与 xlsx 一致；文件名 **`{N}票进仓单_{YYYYMMDD}.pdf`**。**Windows**：本机安装 Microsoft Excel + `pip install pywin32`（`requirements.txt` 在 win32 平台会自动带上）。**Linux**：安装 LibreOffice，或设置 **`YOUZI_LIBREOFFICE`** 指向 `soffice` 可执行文件
  - **`dps_warehouse`**：收货地址多行文本，键 **`SHENZHEN`** / **`YIWU`**（与进仓单预览、表头一致）
  - **`dps_warehouse_entry_remarks`**（可选）：特殊备注栏 `{特殊备注}`，按仓键字符串，如 `"SHENZHEN": "…"`, `"YIWU": "…"`
  - 响应 `{ code, msg, total, rows }`，按 `total` 与 `pageSize`（默认 10）自动翻页。见 `services/shipment_query_config.py`
  - **DPS 运单同步批处理**（计划任务页）：`shipment_queryByPerson` / `_pickup` / `_warehoused` 三项可分别开关，共用发运时间范围；**默认均关闭**，约 24 小时各执行一次。见 `services/shipment_dps_sync.py`
  - **同步哪些字段**：`youzi_v2/config/shipment_dps_sync_fields.json`（`onInsert` / `onUpdate`）；映射逻辑见 `services/shipment_dps_mapper.py`（`customer_no`←`internalOrderNum`，`ref_shipment_no`←`assOrderNumber`）

```json
"dps_authorization": "Bearer <token>",
"shipment_queryByPerson": {
  "url": "https://.../customPageSalesAssistant?pageSize=10&salesAssistantId=...&status=3"
},
"shipment_queryByPerson_pickup": {
  "url": "https://.../customPageSalesAssistant?pageSize=10&salesAssistantId=...&status=01"
},
"shipment_queryByPerson_warehoused": {
  "url": "https://.../customPageSalesAssistant?pageSize=10&salesAssistantId=...&status=1"
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
},
"dps_warehouseform_download": {
  "url": "<排仓单 URL>",
  "method": "POST"
},
"dps_warehouse_entry_download": {
  "url": "<进仓单 URL，可省略以复用排仓单>",
  "method": "POST",
  "warehouseQueryParam": "warehouseCode"
},
"dps_warehouse": {
  "SHENZHEN": "<深圳仓收货地址，多行文本>",
  "YIWU": "<义乌仓收货地址，多行文本>"
}
```

明细状态轻量同步：`POST /api/v1/shipments/sync-route-status-from-dps`（可选 `shipmentNos`，空则全部）；批处理 `POST /api/v1/scheduled-tasks/run-dps-route-status-sync`。按运单 `waybill_id` 请求配置 URL 并回写 `route_status`。
- 承运商：`vendors` 数组，由 `services/carrier_vendors.py` 按 `platform` 读取；同一承运商多套系统时可在主 vendor 配置 **`fallbackVendor": "SENLEI2"`**（或 `fallbackVendors` 数组），主系统无轨迹时按序尝试备用
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
