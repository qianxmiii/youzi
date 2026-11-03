# API 文档

## 目录

- [概述](#概述)
- [通用约定](#通用约定)
- [健康检查](#健康检查)
- [工作台 workbench](#工作台-workbench)
- [常用工具 tools](#常用工具-tools)
- [运单 shipments](#运单-shipments)
- [船期 vessel-schedules](#船期-vessel-schedules)
- [海运预警 maritime-alerts](#海运预警-maritime-alerts)
- [客户与渠道](#客户与渠道)
- [统计与计划任务](#统计与计划任务)
- [地址簿](#地址簿)
- [码表与字典](#码表与字典)
- [Legacy API](#legacy-api)

Base URL（开发）：`http://127.0.0.1:3001`

前端通过 Vite 代理访问 `/api/*`。

## 概述

路由定义在 `youzi_v2/app.py`，请求/响应模型在 `schemas/`。新接口统一使用 `/api/v1/` 前缀；部分 Legacy 路径仍保留 `/api/` 无版本号。

## 通用约定

- 请求体：JSON（`Content-Type: application/json`），文件上传用 `multipart/form-data`
- 时间字段：字符串 `YYYY-MM-DD HH:mm:ss` 或 ISO 日期
- 错误：HTTP 4xx/5xx + JSON `{ "detail": "..." }`
- 分页：多数列表接口支持 `page`、`page_size` 或 `limit`/`offset`（以各接口为准）

## 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 新前端健康检查 |
| GET | `/api/health` | Legacy 兼容 |

```bash
curl http://127.0.0.1:3001/api/v1/health
```

## 工作台 workbench

前缀：`/api/v1/workbench`  
设计说明：[design/logistics-workbench-home-redesign.md](./design/logistics-workbench-home-redesign.md)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/workbench/overview` | 首页聚合：`focus` / `todos` / `arrivals` / `routeStatus` / `overview`（模块级 `available`/`error` 容错） |

查询参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `todoLimit` | 8 | 待处理事项条数上限（1–20） |
| `arrivalLimit` | 6 | 近期到港聚合条数上限（1–20） |

响应要点：

- `generatedAt`：生成时间
- `focus`：待处理异常（SLA `pendingOpen`）、待催收（催款 `todoCount`）、轨迹审批（`pendingTrackingTimeReview`）、三天内到港（海运 `arrivingSoon`）
- `todos.items`：异常 / 催款 / 轨迹审批合并，同票合并展示，统一优先级后截断
- `arrivals.items`：ETA 在「往前 3 天～往后 3 天」且尚无 ATA；`dayGroup` 为 `past`（往前三天内）/ `today` / `forward`（往后三天内）；按船名航次+目的港+ETA 聚合
- `overview`：在途（`IN_TRANSIT` 未签收）、查验中（`exception_code=INSPECTION`）、已到港未签收、本周签收（本地周一～周日）
- `routeStatus`：未签收运单按关键明细状态计数；`missingCount` 为空或信息传递；`todayItems` 为今日动态（7 项：离港 ATD、到港 ATA、内签收 `delivered_time`、异常开始、到中转仓/快递交仓/轨迹签收明细节点时间，均本地自然日）；点击跳转运单列表日期或 `timeField` 筛选

```bash
curl "http://127.0.0.1:3001/api/v1/workbench/overview?todoLimit=8&arrivalLimit=6"
```

## 常用工具 tools

前缀：`/api/v1/tools`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/tools/image-link-zip/jobs` | 上传 Excel，启动后台下载任务，返回 `jobId` |
| GET | `/api/v1/tools/image-link-zip/jobs/{jobId}` | 查询进度（`done`/`total`/`status`） |
| GET | `/api/v1/tools/image-link-zip/jobs/{jobId}/download` | 完成后下载 zip |
| POST | `/api/v1/tools/shipment-file-rename/parse` | 解析运单 Excel，返回重命名映射（运单号/国家/仓库代码或邮编/件数 → `targetStem`；无仓库代码时用邮编）；浏览器递归扫描子文件夹后本地改名 |
| POST | `/api/v1/tools/product-import` | 上传箱单发票，转换为产品导入模版；form 字段 `invoice` |
| GET | `/api/v1/tools/product-import/download/{taskId}` | 下载生成的产品导入 .xls |

查询参数：`column`（默认 `P`，创建任务时）。表单字段：`file`（`.xls` / `.xlsx`）。

```bash
# 1) 创建任务
curl -X POST "http://127.0.0.1:3001/api/v1/tools/image-link-zip/jobs?column=P" \
  -F "file=@youzi_v2/tools/temp/datapic.xls"
# 2) 轮询进度
curl "http://127.0.0.1:3001/api/v1/tools/image-link-zip/jobs/{jobId}"
# 3) 下载
curl -O -J "http://127.0.0.1:3001/api/v1/tools/image-link-zip/jobs/{jobId}/download"
```

## 运单 shipments

前缀：`/api/v1/shipments`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 列表（筛选、分页；含 `workspace`（`preport` 港前 / `transit` 在途，与 DPS Status 划分一致，未传 `statusCode` 时按工作台限定范围）、`statusCode`、`routeStatus`、`supplierName`（供应商精确匹配）、`originWarehouseCode`（收货仓精确匹配）、`missingRouteStatus`、`missingAmazonRefs`（派送仓库恰好 4 位，且货件号或亚马逊预约号为空或仅为 `1`）、`groupId`、`groupNo`、`hasGroup`、`noZipcode` 等；响应含 `routeStatus`） |
| GET | `/{item_id}` | 单条详情 |
| POST | `/` | 新建 |
| PUT | `/{item_id}` | 更新运单字段。补货件号窗口传 `pushAmzUpdate=true` 时，保存成功后尝试推送亚马逊，响应附带 `amzPush` |
| GET | `/{item_id}/amz-push-preview` | 预览本次将推送的起运港、目的港（不调用 DPS） |
| DELETE | `/{item_id}` | 删除 |
| POST | `/batch-delete` | 批量删除 |
| PATCH | `/batch-update` | 批量更新字段 |
| GET | `/filter-options` | 筛选项（含 `supplierNames`、`originWarehouseCodes`、`groups`、`routeStatuses`：`{ code, nameZh, dpsStatus }`） |
| GET | `/export` | Excel 导出 |
| POST | `/import` | Excel 导入 |
| POST | `/sync-tracking` | 同步内部轨迹（完成后自动评估相关分组提醒，见响应 `groupAlertsCreated`） |
| POST | `/sync-carrier-tracking` | 同步承运商轨迹（同上） |
| POST | `/sync-from-dps` | 按运单号从 DPS `shipment_queryByOrder` 拉取并 upsert（body: `shipmentNos`，最多 200）。同时写入应收 `receivable`、应付 `proRecCharge`、利润 `profit`（均为人民币）和利润率 `profitRate` |
| POST | `/sync-preport-from-dps` | 港前全部更新：已下单、提货中、已入仓（不含已取消），按运单号走同一 `shipment_queryByOrder` 写入；无 body |
| POST | `/download-dps-cargo-data` | DPS 货箱（`dps_data_download`）；body: 本地运单 `ids`，最多 50；单票 `{运单号}_data.ext`，多票 `{N}票数据_{YYYYMMDDHHmmss}.zip`（内含同名文件夹与各票 `_data` 文件） |
| POST | `/dps-export-jobs` | 异步 DPS 导出（body: `exportType`、`ids`、可选 `splitSpec`；`exportType=markRename` 另需 `renameFields`、`renameSeparator`）。唛头（重命名）逐票下载，文件名按字段顺序拼接，空字段跳过；`addressCode` 为空时回退邮编；可选 `renameFolder`（如 `customerNo`）把相同值放进同一目录；`renameCountryLang`=`en`（默认国家码缩写如 AU）/`zh`（中文名）控制国家字段。单票且未选文件夹时直接下载该文件名，否则 zip `{N}票{M}件唛头_{时间}.zip`（M 为成功下载票的件数合计）。例：`shipmentNo`+`addressCode`+`ctns`、分隔符 `-` → `运单号-派送仓库或邮编-件数.pdf`。`exportType=markSelf`（唛头自生成）不调 DPS：按件数生成本地 102mm×102mm PDF（渠道英文名 / 运单号 / 客户单号 / Code128=运单号+4位箱序 / `PKG:i/N` / 国家码 / 邮编 / `MADE IN CHINA`）；单票 `{运单号}.pdf`，多票 `{N}票{M}件唛头(自生成)_{时间}.zip`。返回 `jobId`，轮询 `GET /dps-export-jobs/{id}`，完成后 `GET …/download` |
| GET | `/dps-export-jobs/{job_id}` | 导出进度 `{ progress, message, done, failed }` |
| GET | `/dps-export-jobs/{job_id}/download` | 导出完成后的文件 |
| POST | `/download-dps-mark-data` | DPS 唛头（1 票 `dps_mark_download`，多票 `dps_batchmark_download`）；多票保存名 `{N}票{M}件唛头_{时间}.zip`；body: 本地运单 `ids`（前端下载菜单已改用 `/dps-export-jobs` 以展示进度） |
| POST | `/download-dps-mark-data-split` | **单票**唛头 PDF 按件数拆分；body: `ids`（长度 1）、`splitSpec`（如 `1 2 2`）或 `segments`；包内 `{运单号}_{起-止}_{n}ctns.pdf`（单页为 `{运单号}_{序号}_{n}ctns.pdf`），zip `{运单号}_{总件数}ctns.zip` |
| POST | `/download-dps-packinglist` | DPS 箱单发票（`dps_packinglist_download`，转发为 `?ids=` 逗号拼接 waybillId）；单票 `{运单号}_箱单发票.ext`，多票 DPS 原名 |
| POST | `/download-dps-warehouseform` | DPS 排仓单（`dps_warehouseform_download`，`?ids=` 逗号拼接；勾选超过 50 票自动分批请求，多批打包 zip）；单票 `{运单号}_排仓单.ext` |
| POST | `/receive-warehouse-entry-preview` | 进仓单预览：收货仓键、`config.dps_warehouse` 收货地址文案（勾选运单须同一收货仓） |
| POST | `/download-dps-warehouse-entry` | 进仓单（`warehouse_entry_template.xlsx` 模板填充 + `dps_warehouse` 收货地址）；**`{N}票进仓单_{YYYYMMDD}.xlsx`** |
| POST | `/download-dps-warehouse-entry-pdf` | 进仓单 PDF（先按模板生成 xlsx 再转 PDF，与 Excel 下载版式一致）；**`{N}票进仓单_{YYYYMMDD}.pdf`**；无 Excel/LibreOffice 转换能力时 503 |
| POST | `/sync-route-status-from-dps` | 明细状态：按 `waybillId` 调 `config.dps_route_status_query`；`shipmentNos` 可选（最多 200），空则全部 |
| GET | `/tracking-freshness-stats` | 轨迹新鲜度统计；含 `missingAmazonRefs`（转运中、派送仓库恰好 4 位，且货件号或亚马逊预约号为空或仅为 `1` 的票数） |
| GET | `/tracking-sync/daily-stats` | 日同步统计 |
| POST | `/exceptions/open` | 开启异常 |
| POST | `/exceptions/close` | 关闭异常 |
| POST | `/check-order-product-ctns` | 核对勾选运单的产品箱数合计与运单件数。body: `ids`，最多 50。一致票只返回 `matched` 计数；不一致与查询失败放在 `issues`（运单号、运单件数、产品总箱数、差额、说明） |
| POST | `/api/v1/shipment-tracking-time-candidates/batch-review` | 批量审批签收时间。body: `ids`（最多 200）、`action`（`use_expected_delivery` 采用预计送仓 / `use_signed_track` 签收节点 / `reject` 暂不处理）。手动填写仍用单条审批 |
| GET | `/{item_id}/order-products` | 运单产品：按 `waybillId` 调 `config.dps_getOrderProduct`（查询参数 `commerceWaybillId`）。只返回 `cnName` 中文品名、`enName` 英文品名、`ctns` 箱数。无运单 ID 时 400 |
| GET | `/{item_id}/tracking-logs` | 内部轨迹 |
| GET | `/{item_id}/carrier-tracking-logs` | 承运商轨迹 |
| POST | `/{item_id}/subscribe` | 订阅轨迹更新 + ETA 到港前每日提醒 |
| DELETE | `/{item_id}/subscribe` | 取消订阅 |
| POST | `/batch-subscribe` | 批量订阅 |
| POST | `/batch-unsubscribe` | 批量取消订阅 |

**催款管理**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/payment-reminders` | 催款列表（`scope` / `customer` / `channelCategory` / `settlementMethod` / `reminderType` / `followupStatus` / `search` / `fclOnly` / `minReceivable` / `sortBy=receivable`；`search` 匹配运单号、客户单号、关联单号、货件号；`channelCategory` 为渠道大类；`fclOnly` 默认 `false` 排除整柜，`true` 仅整柜；`scope=todo` 排除月结；不含港前状态：已下单 `0`、提货中 `01`、已入仓 `1`、已取消 `4`；含 `receivableCny` 应收，人民币。`minReceivable` 只保留达到该金额的票，空应收不计入；`receivablePending=true` 只保留未记应收或应收小于等于 0 的票；`sortBy=receivable` 按应收从高到低，空应收仍在最后） |
| GET | `/payment-reminders/customer-ranking` | 当前筛选下按客户汇总大于 0 的应收，最多 100 名。条内分开已逾期和未逾期。不含 `customer` 筛选，也不含港前状态。`pendingCount` 是未记应收或应收不大于 0 的票数。页面默认收起 |
| GET | `/payment-reminders/summary` | 数量统计：`todoCount` / `allUnpaidCount` / `overdueCount`（侧栏角标、页面标题；默认排除整柜和港前状态；`todoCount`/`overdueCount` 排除月结） |
| GET | `/payment-reminders/export` | 导出当前筛选为 Excel（上限 10000；含 `fclOnly`） |
| GET | `/payment-reminders/{shipment_id}/followups` | 跟进记录 |
| POST | `/payment-reminders/{shipment_id}/followups` | 新增跟进 |
| POST | `/payment-reminders/collection-term` | 给选中运单设置收款起算日。body: `shipmentIds`、`collectionStartDate`、`paymentTermDays`、`reminderAdvanceDays`。账期可填天数，也可直接选收款截止日，保存时换算为天数。应付款日 = 起算日 + 账期，到期前 `reminderAdvanceDays` 天进入待催 |

**订阅消息（顶栏 · 消息铃铛）**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/shipment-subscriptions/notifications` | 未读轨迹订阅通知（`items` + `unreadCount`） |
| POST | `/api/v1/shipment-subscriptions/notifications/read-all` | 全部标为已读 |
| POST | `/api/v1/maritime-alerts/shipment-arrivals/{id}/read` | 单条海运到港通知已读 |

**分组待办（顶栏 · 待办图标）**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/shipment-group-notifications?scope=todo` | 未处理待办（`items` + `pendingCount`，按 `resolved_at` 为空） |
| GET | `/api/v1/shipment-group-notifications?scope=unread` | 未读分组提醒（首页批次提醒等，`unreadCount`） |
| POST | `/api/v1/shipment-group-notifications/{id}/resolve` | 标记已处理（从待办移除） |

**运输时效预警 / 异常跟踪**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/shipment-sla-alerts` | 预警列表（`scope=todo` 默认待办：未签收且 open/acknowledged，**按运单合并只保留最严重一条**；已跟进整组排最后，组内按严重度；`scope=all` 含历史且逐条，同样已跟进在后；筛选见 `riskLevel` / `alertType`、`exceptionPhase`（`pre_port` 港前 / `post_port` 港后，港后含仅时效预警无人工异常码的单）等） |
| GET | `/api/v1/shipment-sla-alerts/summary` | 工作台摘要计数（`pendingOpen` 按运单号去重） |
| GET | `/api/v1/shipment-sla-alerts/todo-notifications` | 顶栏待办（已超时/严重超时且 open；按运单合并，`pendingCount` 按运单去重；项含 `alertTypes` / `relatedAlertIds`） |
| POST | `/api/v1/shipment-sla-alerts/evaluate` | 手动触发扫描（含孤儿清理、重绑、同单同类型去重） |
| POST | `/api/v1/shipment-sla-alerts/batch-follow-up` | 批量已跟进（body: `{ ids }`，最多 200） |
| POST | `/api/v1/shipment-sla-alerts/batch-resolve` | 批量已解决（body: `{ ids }`，最多 200） |
| POST | `/api/v1/shipment-sla-alerts/{id}/follow-up` | 记录跟进（置为 acknowledged） |
| POST | `/api/v1/shipment-sla-alerts/{id}/acknowledge` | 同 follow-up（兼容） |
| POST | `/api/v1/shipment-sla-alerts/{id}/resolve` | 标记已解决 |
| POST | `/api/v1/shipment-sla-alerts/{id}/ignore` | 忽略 |
| POST | `/api/v1/shipment-sla-alerts/{id}/convert` | 转为人工异常（默认 `TRANSIT_TIMEOUT`） |
| GET | `/api/v1/channels/{code}/sla-rules` | 渠道时效规则 |
| PUT | `/api/v1/channels/{code}/sla-rules` | 保存渠道时效规则 |

**列表示例**

```bash
curl "http://127.0.0.1:3001/api/v1/shipments?limit=20&workspace=transit&statusCode=2&routeStatus=TRACK_SIGNED"
curl "http://127.0.0.1:3001/api/v1/shipments?limit=20&workspace=preport"
```

**Excel 导入**

表头需与 `youzi_v2/config/shipment_excel_columns.json` 一致。

```bash
curl -X POST "http://127.0.0.1:3001/api/v1/shipments/import" \
  -F "file=@运单数据.xlsx"
```

## 船期 vessel-schedules

前缀：`/api/v1/vessel-schedules`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 航次列表 |
| GET | `/{voyage_id}` | 航次详情（含挂靠） |
| GET | `/{voyage_id}/shipments` | 关联运单 |
| POST | `/` | 新建航次 |
| PATCH | `/{voyage_id}` | 更新 |
| DELETE | `/{voyage_id}` | 删除 |
| GET | `/template` | 下载 Excel 模板 |
| POST | `/import` | Excel 导入 |
| GET | `/providers` | 船期数据源 |
| GET | `/vessels/search` | 船名搜索 |
| GET | `/fetch/preview` | 预览外部船期 |
| POST | `/fetch/sync` | 同步外部船期 |
| POST | `/port-calls/{port_call_id}/subscribe` | 港口订阅 |
| DELETE | `/port-calls/{port_call_id}/subscribe` | 取消港口订阅 |

**Excel 导入**

表头见 `config/vessel_schedule_excel_columns.json`；同一 `vessel_voyage` 多行表示多港挂靠。

```bash
curl -O "http://127.0.0.1:3001/api/v1/vessel-schedules/template"
curl -X POST "http://127.0.0.1:3001/api/v1/vessel-schedules/import" -F "file=@船期.xlsx"
```

## 海运预警 maritime-alerts

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/maritime-alerts/overview` | 首页预警概览（含海运状态计数与 `inspection` 查验中票数） |
| POST | `/api/v1/maritime-alerts/port-arrivals/{id}/read` | 标记港口到港已读 |
| POST | `/api/v1/maritime-alerts/shipment-arrivals/{id}/read` | 标记运单到港已读 |
| POST | `/api/v1/maritime-alerts/notifications/read-all` | 全部已读 |

## 客户与渠道

| 前缀 | 说明 |
|------|------|
| `/api/v1/customers` | CRUD + `sync-from-shipments`；`PATCH` 支持 `customerName` + `updateShipments` 批量改运单客户字段，同时更新客户地址簿里的同一客户名；`GET /export` 导出 Excel（`search`、`vipOnly`，上限 10000 条） |
| `/api/v1/customer-addresses` | 客户地址簿。见下一节 |
| `/api/v1/channels` | CRUD + `seed-defaults`（清空后全量导入渠道清单）、`/meta`；字段含 `dpsChannelName`（DPS cnName）；`PATCH` 可改 `code`，同步更新运单 `channel_code` |

### 客户地址簿

与 `/api/addresses`、`/api/addresses-warehouse` 分开。数据在本地库 `customer_addresses`，不进入 Git。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/customer-addresses` | 列表。`customer` 精确匹配客户名；`addressKind` 为 `WAREHOUSE` / `COMMERCIAL` / `RESIDENTIAL`；`remote` 是否偏远；`search` 模糊匹配简称和联系字段 |
| POST | `/api/v1/customer-addresses` | 新建。客户名必须已在客户管理中 |
| PUT | `/api/v1/customer-addresses/{id}` | 修改 |
| DELETE | `/api/v1/customer-addresses/{id}` | 删除一条 |
| POST | `/api/v1/customer-addresses/batch-delete` | body: `ids`，最多 500 |
| GET | `/api/v1/customer-addresses/export` | 按当前筛选导出，上限 10000 |
| GET | `/api/v1/customer-addresses/template` | 导入模板，示例为虚构数据 |
| POST | `/api/v1/customer-addresses/import` | 上传 `.xlsx`，只新增。客户不存在或必填缺失的行跳过 |

## 订单流转 order-flow

独立于运单。鉴权用 `config.json` 的 `dps_ddlz_authorization`，列表地址用 `dps_ddlz_getOrders.url`。定时拉取默认关闭，间隔 5 分钟。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/order-flow/summary` | 含 `mineCount`（未结束的销售-）和 `unseenCount`（上次打开铃铛后新进入节点的单数），以及 `listSeenAt`（上次离开订单流转页的时间） |
| POST | `/api/v1/order-flow/list-seen` | 离开订单流转页时记下已查看。列表 NEW 只标这次进来之前还没看过的状态变化 |
| GET | `/api/v1/order-flow/nodes` | 按当前节点汇总票数，以及其中未查看的新进入数 |
| GET | `/api/v1/order-flow/statuses` | 已出现过的当前状态，供筛选 |
| GET | `/api/v1/order-flow/{waybillNo}/logs` | 该票每次进入节点的状态、节点时间和记入时间。更早的节点只保留当前和上一节点，之后的变化会逐条累加 |
| POST | `/api/v1/order-flow/reminders/seen` | 把当前新节点记为已查看。菜单和顶栏角标仍显示未结束的待处理单数 |
| GET | `/api/v1/order-flow` | 本地快照。`scope`：`mine` 待处理、`remind` 待提醒、`active` 流转中、`ended` 已结束、`all` 全部。可按 `status`、`customer`、`warehouse`、`country`、`channel` 筛选。`channel` 可多选，多个值用逗号分隔。仓库、国家和渠道只显示斜杠前的中文 |
| GET | `/api/v1/order-flow/customers` | 已出现过的客户，供筛选 |
| GET | `/api/v1/order-flow/warehouses` | 已出现过的仓库（去掉斜杠后的代码），供筛选 |
| POST | `/api/v1/order-flow/refresh` | 立即向流转系统拉全量并更新快照 |
| PUT | `/api/v1/order-flow/settings` | `{ enabled }` 开关 5 分钟定时拉取 |

## 报价跟进 quote-opportunities

前缀：`/api/v1/quote-opportunities`  
设计说明：[design/quote-followup-management-design.md](./design/quote-followup-management-design.md)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/quote-opportunities` | 列表。`currentQuotedAmount` 为各渠道总价之和。`profitTotal` 为利润单价乘计费重；报价币种为 USD 时再除以 `exchangeRate`（1 USD 兑 RMB，默认 6.7）后以 USD 显示。`currentProfitRate` 为利润合计除以当前报价，单位是百分比 |
| GET | `/api/v1/quote-opportunities/notifications/summary` | 待办铃铛聚合：今日/逾期/即将过期 |
| POST | `/api/v1/quote-opportunities/parse` | 解析粘贴的日常报价原文，不写入。渠道行支持 `usd/kg`、`usd/cbm`、`rmb/kg`、`rmb/cbm`。返回仓点、渠道行、原文合计、提货费和未识别行 |
| GET | `/api/v1/quote-opportunities/customer-products` | 某客户以往报过的产品名（`customerId` 或 `customerName`） |
| POST | `/api/v1/quote-opportunities` | 新增报价（同时创建 V1）。可带 `destinations` 明细、合计、`pickupFee`、`sourceText`、`profitAmount`、`profitUnit`（`RMB/KG` 或 `RMB/CBM`）、`note` 询价备注。粘贴保存的下次跟进日为当天，以便出现在待办 |
| PUT | `/api/v1/quote-opportunities/{id}/content` | 改正当前报价的客户、产品、费用和仓点渠道，不另开版本 |
| GET | `/api/v1/quote-opportunities/{id}` | 详情，含当前版本的渠道明细 |
| PATCH | `/api/v1/quote-opportunities/{id}` | 更新基础信息/状态/有效期（不直接覆盖报价金额） |
| POST | `/api/v1/quote-opportunities/{id}/followups` | 新增跟进；`adjustQuote=true` 时创建新版本 |
| GET | `/api/v1/quote-opportunities/{id}/versions` | 报价版本历史 |
| GET | `/api/v1/quote-opportunities/{id}/followups` | 跟进记录 |
| POST | `/api/v1/quote-opportunities/{id}/mark-won` | 标记已成单 |
| POST | `/api/v1/quote-opportunities/{id}/mark-lost` | 标记已丢单 |
| POST | `/api/v1/quote-opportunities/{id}/cancel` | 取消 |
| POST | `/api/v1/quote-opportunities/{id}/extend-deadline` | 延长有效期 |

```bash
curl -s "http://127.0.0.1:3001/api/v1/quote-opportunities?scope=todo&limit=20"
```

## 运单分组

前缀：`/api/v1/shipment-groups`（阶段一 CRUD/成员；阶段二规则提醒）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/shipment-groups/meta` | 分组类型元数据（`groupTypes`：value/label/description） |
| GET | `/api/v1/shipment-groups` | 分组列表（`search`、`hasRule`、`hasUnread`、`groupType`、`paymentStatus`、`customer`；每项含 `unreadNotificationCount`） |
| POST | `/api/v1/shipment-groups` | 新建分组（`groupNo` 可省略，自动生成 `GYYMMDDnnn`） |
| GET | `/api/v1/shipment-groups/{id}` | 分组详情（含 `members`、`rules`、统计与 `unreadNotificationCount`） |
| PUT | `/api/v1/shipment-groups/{id}` | 更新分组 |
| DELETE | `/api/v1/shipment-groups/{id}` | 删除分组及成员/规则/提醒 |
| POST | `/api/v1/shipment-groups/{id}/members` | 批量添加成员（`shipmentIds`、`role`、`batchNo`） |
| DELETE | `/api/v1/shipment-groups/{id}/members` | 批量移出成员（body: `shipmentIds`） |
| PATCH | `/api/v1/shipment-groups/{id}/members/batch` | 批量更新成员角色/批次（如标记 `LAST_BATCH`） |
| GET | `/api/v1/shipment-groups/{id}/notifications` | 分组提醒列表（`unreadOnly`） |
| POST | `/api/v1/shipment-groups/{id}/evaluate-alerts` | 手动重新计算提醒 |
| POST | `/api/v1/shipment-group-notifications/{id}/read` | 单条提醒已读 |
| POST | `/api/v1/shipment-group-notifications/{id}/resolve` | 单条提醒标记已处理（同时已读） |
| POST | `/api/v1/shipment-group-notifications/read-all` | 全部已读（可选 `groupId`） |
| POST | `/api/v1/shipment-groups/suggestions/preview` | 推荐分组预览（body: `shipmentIds`，至少 2 票） |
| POST | `/api/v1/shipment-groups/suggestions/apply` | 确认创建推荐分组（body: `items`） |
| GET | `/api/v1/shipment-group-notifications` | 顶栏/首页提醒（`scope=unread` 未读 / `scope=todo` 待办） |

分组详情 `GET .../{id}` 返回 `members` 数组；响应含 `primaryType`、`groupTypes`（`groupType` 与 `primaryType` 相同，兼容旧客户端）。

创建/更新 body 示例：

```json
{
  "groupName": "客户A 6月第一批",
  "primaryType": "PAYMENT_BATCH",
  "groupTypes": ["CUSTOMER_BATCH", "PORT_BATCH", "PAYMENT_BATCH"]
}
```

- `groupTypes` 至少一项；`primaryType` 须包含在 `groupTypes` 中。
- 仅传旧字段 `groupType` 时，等价于 `primaryType = groupType` 且 `groupTypes = [groupType]`。

```bash
curl -X POST "http://127.0.0.1:3001/api/v1/shipment-groups" \
  -H "Content-Type: application/json" \
  -d '{"groupName":"6月批次","primaryType":"PAYMENT_BATCH","groupTypes":["CUSTOMER_BATCH","PAYMENT_BATCH"],"customer":"Acme"}'

curl -X POST "http://127.0.0.1:3001/api/v1/shipment-groups/{id}/members" \
  -H "Content-Type: application/json" \
  -d '{"shipmentIds":["运单UUID"],"role":"NORMAL"}'

curl -X PATCH "http://127.0.0.1:3001/api/v1/shipment-groups/{id}/members/batch" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"shipmentId":"运单UUID","role":"LAST_BATCH","batchNo":"2"}]}'

curl -X POST "http://127.0.0.1:3001/api/v1/shipment-groups/{id}/evaluate-alerts"
```

curl -X POST "http://127.0.0.1:3001/api/v1/shipment-groups/suggestions/preview" \
  -H "Content-Type: application/json" \
  -d '{"shipmentIds":["运单UUID-1","运单UUID-2"]}'

curl -X POST "http://127.0.0.1:3001/api/v1/shipment-groups/suggestions/apply" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"suggestionKey":"...","shipmentIds":["运单UUID"],"groupName":"6月批次","groupType":"ORDER_BATCH"}]}'
```

**运单 Excel 分组列（可选）**：`分组编号`、`分组名称`、`批次号`、`是否最后一批`（见 `config/shipment_excel_columns.json` 的 `group_import_columns`）。

**运单列表分组筛选**

```bash
curl "http://127.0.0.1:3001/api/v1/shipments?noZipcode=true&limit=20"
curl "http://127.0.0.1:3001/api/v1/shipments?hasGroup=true&limit=20"
curl "http://127.0.0.1:3001/api/v1/shipments?groupType=ORDER_BATCH&limit=20"
curl "http://127.0.0.1:3001/api/v1/shipments?groupId={分组UUID}&limit=20"
curl "http://127.0.0.1:3001/api/v1/shipments?groupNo=G260618001&limit=20"
```

列表项 `groups` 示例：

```json
{
  "id": "运单UUID",
  "shipmentNo": "DPSECO260611093",
  "groups": [
    {
      "groupId": "分组UUID",
      "groupNo": "G260618001",
      "groupName": "6月批次",
      "role": "NORMAL",
      "batchNo": ""
    }
  ]
}
```

## 统计与计划任务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/statistics/shipments/overview` | 运单统计概览 |
| GET | `/api/v1/scheduled-tasks/overview` | 计划任务概览 |
| PUT | `/api/v1/scheduled-tasks/settings` | 更新同步配置 |
| GET | `/api/v1/scheduled-tasks/jobs` | 同步任务历史 |
| POST | `/api/v1/scheduled-tasks/run-*-sync` | 手动触发同步 |
| POST | `/api/v1/scheduled-tasks/run-dps-shipment-sync` | DPS 运单全量同步（`shipment_queryByPerson`；body 可选发运时间，默认当月） |
| POST | `/api/v1/scheduled-tasks/run-dps-shipment-sync-pickup` | DPS **提货中**同步（`shipment_queryByPerson_pickup`；发运时间与主任务共用配置） |
| POST | `/api/v1/scheduled-tasks/run-dps-shipment-sync-warehoused` | DPS **已入仓**同步（`shipment_queryByPerson_warehoused`；发运时间与主任务共用配置） |
| POST | `/api/v1/scheduled-tasks/run-dps-shipment-sync-all` | 依次执行提货中、已入仓、在途三项 DPS 运单同步；某一步失败仍继续下一步。body 可选发运时间 |
| POST | `/api/v1/scheduled-tasks/run-dps-route-status-sync` | 更新全部明细状态（有 `waybillId` 的运单；无 body） |
| POST | `/api/v1/notifications/wecom/test` | 企业微信通知测试（详见 [wecom-aibot.md](./wecom-aibot.md)；body 可选 `{ "content": "..." }`） |

## 地址簿

| 前缀 | 说明 |
|------|------|
| `/api/addresses` | 派送地址 CRUD（Legacy 路径） |
| `/api/addresses-warehouse` | 仓库地址 CRUD + 导入/导出/模板 |

## 码表与字典

| 前缀 | 说明 |
|------|------|
| `/api/v1/dict/{dict_type}` | 字典项 |
| `/api/v1/admin/code-tables/*` | 码表管理 + Excel 导入 |

## Legacy API

| 路径 | 说明 |
|------|------|
| `/api/quote-history*` | 报价历史 |
| `/api/product-import*` | 箱单转换 |

完整路由列表以 `app.py` 中 `@app.get/post/...` 为准；变更 API 时必须同步更新本文档。

## 相关文档

- [modules/shipment/README.md](./modules/shipment/README.md)
- [shipment-flow.md](./shipment-flow.md)
- [frontend/src/api/](../frontend/src/api/) — 前端封装

## 运单 DW 窗口

- `GET /api/v1/shipments/{id}/delivery-window`：返回最终窗口、`copyText`、计算依据、警告及保存的设置。
- `POST /api/v1/shipments/{id}/delivery-window/preview`：只预览，不写入设置。
- `PUT /api/v1/shipments/{id}/delivery-window`：保存设置并返回窗口。
- 请求：`mode` 为 `auto` / `range` / `amazon`；`manualStart`、`manualEnd` 为完整 ISO 日期或同时为 null。人工范围必须成对且结束不早于开始；Amazon模式（含auto解析为AMZ）的人工窗口必须是同一周周日至周六，保存不合规窗口返回422，预览返回不可用原因；无效请求返回 422，运单不存在返回 404。
- 渠道时效读写使用 `estimatedDaysMin`、`estimatedDaysMax`（正整数，最短不大于最长）；必须同时填写。旧请求 `estimatedDays` 兼容为相同上下限；响应的兼容 `estimatedDays` 为上限，供原预警使用。旧 `dwEarlyDays`、`dwLateDays` 仅保留兼容，不再参与DW计算。渠道列表返回 `slaEstimatedDaysMin` / `slaEstimatedDaysMax`。
- `copyText` 固定为 `MM/DD - MM/DD`，详情日期保留年份。无规则、无起算日期或已取消时不生成。规则优先匹配同承运商，否则使用渠道通用规则；不借用其他承运商规则。
- 渠道规则增加 `postArrivalDaysMin` / `postArrivalDaysMax`（非负整数，默认7/15，最短不得大于最长）；渠道复制时一并保留。DW优先以ATA、否则ETA计算到港后范围，与离港全程范围分别取较晚起止日期；不改变原SLA预警期限。
- 详细业务规则及首版限制见 [delivery-window.md](./delivery-window.md)。

### DW历史参考

`GET /api/v1/shipments/{id}/delivery-window/history?mode=auto|range|amazon` 为独立只读查询。不存在返回404，无效模式返回422。不修改DW设置或运单。

响应包含 `scope`（实际匹配范围）、`lookbackDays=90`、`minBatchCount=5`、`completedCount`、`independentBatchCount`、`unknownBatchTickets`、`longExceptionCount`、`inTransitCount`、`truncated`、`warnings`、`reason`；`metrics.full/postArrival` 各含 `actual/normal/recent30`，每项含 `ticketCount`、`batchCount`、`p50Days`、`p90Days`。条件满足时返回 `prediction` 的日期、复制范围、依据和警告，否则为null。历史参考不改变原DW查询与复制响应；具体口径与局限见 [delivery-window.md](./delivery-window.md)。
