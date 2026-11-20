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
| GET | `/api/v1/shipment-routes/options` | 新增路由可选的明细状态（含 100 信息传递）及常用节点配置，见[新增路由](./shipment-route-add.md) |
| PUT | `/api/v1/shipment-routes/presets` | 保存本地常用节点配置，最多100项 |
| POST | `/api/v1/shipment-routes` | 单票或批量新增DPS节点，最多50票，返回逐票结果；写请求不自动重试 |
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
| POST | `/sync-today-from-dps` | 港前「同步今天」：当天 00:00:00–23:59:59，依次同步提货中、已入仓（均 `orderTimeStart`/`orderTimeEnd`）；一步失败仍继续；无 body |
| POST | `/sync-today-transit-from-dps` | 在途/港后「同步今天」：当天发运时间（`transitTimeDateRange[0]`/`[1]`），仅 `shipment_queryByPerson` 在途；无 body |
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

同一运单的订阅提醒跨来源合并，仅保留最新生成的一条（按生成时间排序，同秒按写入顺序）；读取列表或计数时，将旧提醒自动置为已读，历史记录保留。最新提醒已读后，旧提醒不会重新出现；列表在合并后分页，未读计数采用相同口径。

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

## 每日同步 daily-sync

订单流转独立入口：`GET /api/v1/order-flow/authorization` 仅返回 `configured`；`POST /api/v1/order-flow/save-and-refresh` 接收只写 `authorization`（空值沿用），完整拉取现有订单流转列表后保存 `dps_ddlz_authorization` 并应用原刷新快照，响应含原 `skipped/reason/remote/created/changed/ended` 及 `authorizationSaved`。拉取或保存失败返回 400；已有执行则返回 `skipped=true` 且不保存授权。只刷新订单流转列表，不执行其他名单同步。详见[操作说明](daily-sync.md#订单流转专用授权)。

- `GET /api/v1/daily-sync`：返回 `configured`（不含凭据）和最近一轮 `run`，无任务为 null。
- `POST /api/v1/daily-sync`：请求包含只写 `authorization`，可选 `resumeId`、`start`、`end`；授权空值沿用已保存配置，不清空旧授权。新任务日期未给时沿用计划任务配置；继续任务忽略新日期并保持原范围。成功返回 HTTP 202 和任务快照（含 `id`、`authorizationSaved`），不等待完整执行。
- 运行状态：`queued`、`running`、`waiting_authorization`、`partial`、`interrupted`、`done`。`steps` 含 `key`、`label`、`status`、`attempt`、`message`、最近一次执行的数字 `stats`、脱敏 `errors`，轨迹阶段另含累计 `candidateCount`、`completedCount`、`pendingCount`；不返回候选单号或凭据。
- 参数/验证/保存失败返回 400；同步租约冲突返回 409。网络超时导致客户端未收到启动响应时，先 GET 核对任务，不盲目重复提交。已有未完成任务必须指定其 `resumeId`，不能另起一轮。
- `POST /api/v1/daily-sync/{id}/close`：仅允许明确结束部分完成、等待授权或已中断任务；状态改为 `closed`，保留错误及未完成明细，任务历史仍显示需关注。之后可另起一轮。运行中返回冲突，不支持将失败记录改成成功。
- 此接口是独立后台任务，不接入请求结束即完成的同步请求中间件；顶部任务中心复用 `task_history` 的 server 记录。实际执行范围、继续语义与单进程限制见 [每日同步说明](daily-sync.md)。

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

明细状态同步 `POST /api/v1/shipments/sync-route-status-from-dps`：DPS 授权失效返回 401 与明确的 `detail`，同步占用返回 409；单票、选中及全部更新均显示服务端具体原因。授权优先读取根级 `dps_authorization`；根级未配置时才回退到接口块中的 `Authorization`。

- [transport-attention.md](./transport-attention.md) — 运输关注阈值读写、人工异常列表和七天跟进接口；待办列表、统计和角标统一排除未关闭人工异常、已签收及已取消运单。
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


### 待销售确认费用

订单流转新增「待销售确认费用」tab，独立于原订单流转快照。配置键为 `dps_ddlz_getPendingSalesFeeOrders`，包含 `url`、`method`，可选 `pageSize`、`timeout`；鉴权复用 `dps_ddlz_authorization`。响应沿用 `code`、`rows`、`total`，订单以 `waybillNo` 去重，展示字段沿用订单流转字段。不提供远端费用确认操作或节点轨迹。

- `GET /api/v1/pending-sales-fees`：返回完整本地名单、`total` 和轮询开关；页面按运单号、客户、状态、渠道、国家、仓库筛选并支持复制单号。
- `POST /api/v1/pending-sales-fees/refresh`：刷新独立名单，返回 `skipped`、`reason`，成功时含 `remote`；同步进行中不重复启动。

复用订单流转的五分钟轮询开关，两类同步独立处理。仅完整分页成功后原子替换费用名单，缺失订单退出该名单；失败保留旧数据。分页要求有效 `rows`、`total` 和运单号，空页、重复页或超过上限但尚未收齐时拒绝更新。原订单流转也使用此完整性校验。

启动时自动创建 `pending_sales_fee_orders` 和 `pending_sales_fee_sync` 表，无需手工迁移。新 tab 不计入原铃铛和菜单待处理数。


### 签收后的到港提醒

通知读取及 ETA 提醒扫描时，状态为 `DELIVERED`（忽略大小写及首尾空格）或签收时间非空的运单，其已有未读 `eta_reminder` 消息自动置为已读。列表和未读计数采用相同规则；内部轨迹、承运商轨迹、签收消息等其他来源不受影响。


### 重命名空格规则

唛头重命名（含前端预览、字段分组文件夹）及 Excel 文件重命名保留字段内部空格，仅清理首尾空白，换行与制表符转换为空格。非法文件名字符沿用原规则过滤或替换，不修改原始运单字段。


### 核对件数结果复制

核对件数窗口提供「复制不一致单号」，仅复制结果中 `kind=mismatch` 的运单号，去重并每行一个；不包含查询失败项。加载中或无不一致票时按钮禁用。


### 全局任务入口

顶部任务入口在当前浏览器会话统一展示批量货件号推送、DPS 导出、件数核对、内部及承运商轨迹手动同步。批量推送显示已处理票数、分类统计及逐票结果；导出使用服务端进度；核对及轨迹接口仅显示运行状态和完成摘要，不虚构百分比。可打开详情、复制结果、清除已完成记录；异常任务未查看时保留橙色提示。记录现已保存至本地数据库，见下方任务历史；刷新、关闭浏览器仍可能中断前端调度；服务端导出不因此自动取消，此入口不提供跨刷新恢复。


全局任务中的件数核对详情保留结构化结果：统计卡片展示已核对、件数一致、件数不一致、查询异常；明细表展示运单号、运单件数、产品箱数、差额和原因。支持按异常类型筛选，以及分别复制不一致单号、查询异常单号和完整结果。没有产品归入查询异常，不当作件数不一致；缺失件数以短横线展示。


### 任务历史（持久化）

升级后创建 `task_history`（摘要、统计及逐票结果）和 `task_operation_events`（批量修改计划及推送结果）表，启动自动迁移。仅记录升级后的任务，无历史回填；不记录鉴权、原始请求配置或报价。记录包含单号与业务字段，按业务数据库权限保护，不提交 Git。当前系统未提供可靠的操作人身份，本功能不声称记录操作者。

- `PUT /api/v1/task-history/{id}`：保存前端任务快照，同一编号更新；只接受任务展示字段。
- `GET /api/v1/task-history?limit=50&offset=0`：按开始时间倒序分页，每页最多 100 条。
- `GET /api/v1/task-history/{id}/events`：读取该批次服务端登记的修改前后值与推送结果。

当前会话在开始、运行进度及结束时保存快照；保存失败显示提示并支持重试。顶部面板自动读取最近 50 条，可刷新历史、加载更多。「隐藏已完成」将任务编号保存在当前浏览器 localStorage（不保存业务结果），刷新后维持隐藏；「查看历史」包含隐藏记录。历史中未结束的任务显示「结果待确认」，不冒充当前运行任务，也不自动重试；刷新不会恢复前端执行。

批量推送把全局任务编号传给 `batch-row` 的 `taskId`，在本地修改前登记货件号、预约号、港口及强制标志，推送后补结果。没有最终结果表示仅登记过操作计划，不证明修改或推送成功；需核对当前数据。该记录为独立服务端操作明细，不以可修改的前端摘要作为修改事实证明。未改变正常保存及失败不回滚的业务规则。后端任务记录与前端摘要可能因断网而存在时间差。


### 链接批量下载

工具中心新增提货照片链接下载及独立持久任务接口，支持粘贴/手工编辑、规则转换、按运单号命名、部分成功汇总包、失败重试和七天文件有效期。接口及运行限制见[链接批量下载](./link-download.md)。此类任务由后端管理，刷新可恢复查看，服务重启中断的票需重试。


手动港前更新全部运单、港前/在途同步今天、更新选中运单及明细状态更新现接入全局任务与历史。结果展示新增、更新、失败等统计，分步骤同步保留各步摘要；业务错误、跳过和部分失败标记为需关注。现有接口仅返回最终结果，运行中显示状态，不展示虚构逐票进度；这类请求仍非可跨刷新恢复执行的后端任务。


全局任务在发起时记录来源菜单名称与路径，任务名称统一包含来源（如「港前运单 · 更新全部运单」「在途运单 · 同步内部轨迹」），详情显示来源，历史保留 `source`、`sourcePath`。切换菜单不改变已创建任务归属；旧任务缺少来源时不推断补写。


运单 Excel 导出（港前、在途共用）和催款 Excel 导出的「状态」列统一使用中文：`0` 已下单、`01` 提货中、`1` 已入仓、`2` 转运中、`3` 已签收、`4` 已取消，兼容旧英文状态码；未知映射保留原值。导入支持上述中文状态，不改变数据库存储码或菜单筛选条件。


### 同步请求运行状态核实

手动运单更新、轨迹同步、件数核对通过 `X-Youzi-Task-Id` 关联已创建的任务。后端在请求执行期间维护活动编号，`GET /api/v1/task-history` 返回 `activeRequestIds`；前端按实际活动集合恢复运行中显示并轮询。后端完成后保存统计、异常及最终状态，避免刷新导致丢失结束结果。`managedBy=request` 记录由后端接管，前端不能覆盖。后端重启后无活动记录的旧运行任务仍标为待确认，不假装继续执行。未带编号的既有客户端保持原接口行为；已经在执行的旧版本请求无法补关联。此关联不提供失败自动重试。


### 任务隐藏与删除

任务中心使用眼睛图标隐藏已完成，当前浏览器持久保存隐藏编号，跨浏览器不共享。历史图标切换完整历史，仍可分批加载；运行中、结果待确认记录不通过隐藏已完成清理。

`DELETE /api/v1/task-history/{id}` 真正删除已结束任务摘要及关联 `task_operation_events`，保留无业务内容的编号墓碑（`task_history_deleted`），防止延迟快照或源任务重新写入而复现。详情列表的删除操作需明确确认，不能删除数据库中仍为 running 的任务。删除不撤销运单修改或远端推送，不删除下载文件，不影响下载工具自身的任务记录。部署后需重启后端创建墓碑表。已执行的删除无法恢复，前端也会忽略删除前的迟到历史响应。


### 港前标识

新增配置目录及批量管理接口，列表返回 `commerceMarkIds`、`commerceMarks`（名称、颜色），源数据优先读取 `params.markVos`，兼容顶层 `markVos`。列表及导出支持 `commerceMarkIds` 多选任意匹配；POST `commerce-marks` 对应增加、移除和替换，成功后本地回写。配置及操作限制见[标识管理](./commerce-marks.md)。


标识目录现由后台 `commerce_mark_codes` 码表维护，编码对应 DPS 标识 ID，新增 `color` 字段及 `hasMarkFields` 元信息；支持名称唯一性校验、排序、启停用及 Excel 模板导入。仅启用项可用于操作，名称映射同步包含停用项；旧 JSON 标识目录一次性迁移，接口地址和鉴权继续保留在私密配置中。


`POST /api/v1/commerce-marks/sync`：从 `dps_getMarks` 同步到标识码表，返回 `total`、`created`、`updated`、`unchanged`、`failed`；保留已有排序与启用状态，不删除远端未返回项。支持请求任务 ID 关联全局任务。响应结构和配置详见[标识管理](./commerce-marks.md#同步标识目录)。


运单标识已迁入 `shipment_marks`，列表、详情和 `commerceMarkIds` 筛选参数保持兼容，返回的 `commerceMarks` 仍含 ID、名称和颜色。缺少 ID 的标识保留名称键，不要求一定存在目录项；主表旧 JSON 不再作为来源，迁移及回退见[关联表迁移](./commerce-marks.md#运单标识关联表迁移)。

### 港前／在途运单实重与体积

运单列表、详情及新增／更新返回 `actualWeight`（实重 kg）、`volumeCbm`（体积 m³），未同步时为 null。写入模型支持同名驼峰或 `actual_weight`、`volume_cbm`，须为有限非负数值。DPS 同步分别取 `params.roughWeightTotal`、`params.volumeTotal`，缺失或无效时不覆盖已保存值；零值正常同步。港前和在途的列设置均可勾选「实重（kg）」「体积（m³）」，默认不增加可见列。升级需重启后端自动补列并重新同步运单，页面显示不改变已保存的数值精度。

运单「复制 → 数据（按方）」沿用原数据摘要格式，第二行使用已保存的 `volumeCbm`，仅复制输出向上取整保留两位小数，单位 cbm，不改变数据库原值；缺失或无效体积显示 `—`，零值输出 0.00cbm。英文客户用 Chargevolume 标签（如 `Chargevolume: 3.25cbm`），末尾沿用中英文确认句；原「数据」仍复制计费重。

运单导出（`GET /api/v1/shipments/export`）的「渠道」列优先显示关联码表的中文名 `channelNameZh`，中文名缺失或为空时回退 `channelCode`。港前和在途共用此规则，筛选及存储仍使用渠道编码。
