# 运单业务流程

## 目录

- [概述](#概述)
- [生命周期](#生命周期)
- [数据录入](#数据录入)
- [轨迹同步](#轨迹同步)
- [异常管理](#异常管理)
- [船期关联](#船期关联)
- [到港订阅与预警](#到港订阅与预警)
- [注意事项](#注意事项)

## 概述

运单（Shipment）是 Youzi v2 的核心业务对象，贯穿录入、在途跟踪、异常处理、海运节点与签收。前端按 DPS **Status** 拆为 **`/shipments/pre-port`（港前）** 与 **`/shipments`（在途）**，共用 `ShipmentsView.vue`；列表 API 传 `workspace=preport|transit`。港前页「更新全部运单」调用 `POST /api/v1/shipments/sync-preport-from-dps`，按运单号走 `shipment_queryByOrder`，范围是已下单、提货中、已入仓，不含已取消；与「更新选中运单」同一写入。

## 生命周期

```text
创建/导入 → 待发货/在途(IN_TRANSIT) → 轨迹更新 → 签收(delivered_time)
                ↓
            异常开启 → 处理 → 异常关闭
```

粗状态存 `shipments.status_code`（码表 `shipment_status_codes`）；DPS 轨迹明细状态存 `shipments.route_status`（码表 `shipment_route_status_codes`，来自 `commerceWaybillRouteInfo.status`）。粗状态：`signingTime` 或内部轨迹 API `status=3` → `DELIVERED`；**不**因 601 / `markVos` 单独判粗状态签收（601 只映射明细 `TRACK_SIGNED`）。运单列表「状态」列：**粗状态已为已签收时显示「已签收」**，悬停可见明细（如轨迹签收）；仅明细 601 而粗状态仍转运中时显示「轨迹签收」。

异常跟踪**待办退出**（不再出现在默认列表）：明细 `TRACK_SIGNED`，或粗状态 `DELIVERED` / 有 `delivered_time`（与运单列表「已签收」一致）。**阶段卡点起算**仍以明细节点时间为准（202 入库 / 306 到港 / 502 到中转仓，写入 `route_*_time`），不以粗状态或 `ATA` / `warehouse_entry_time` 起算。

异常跟踪的运输预警、人工异常待办及提醒仅适用于未签收的在途运单。历史视图可回看在途工作台中的已签收运单。

DPS 同步后：明细状态 206/402 自动开启清关异常；最新关键节点离开这两类时自动解除（不覆盖掉件等人工异常）。异常跟踪中「到仓未派送」预警在明细为 **509 卡派已约仓** 时展示为 **约仓未派送**。**更新明细状态**（`dps_route_status_query`）时除 `route_status` 与阶段 `route_*_time` 外，若轨迹含 **301/306** 且本地 **ATD/ATA 为空**，按节点最早时间回写 `atd`/`ata`（不覆盖已有值）。工作台首页有未签收明细状态漏斗，点击可跳转运单列表。详见 [design/shipment-route-status-design.md](./design/shipment-route-status-design.md)。

## 数据录入

三种方式：

1. **单条表单**：`POST /api/v1/shipments`（`ShipmentFormModal.vue`）；承运商从码表 `carrier_codes` 下拉选择，界面显示中文名，提交时写入 DPS `carrier_id`（字段 `carrier_code`）
2. **Excel 批量导入**：`POST /api/v1/shipments/import`（列映射见 `config/shipment_excel_columns.json`；可选分组列：分组编号、分组名称、批次号、是否最后一批，按 `group_no` 自动建组/加成员）
3. **推荐分组**：勾选运单后「分组 → 推荐分组」，或 `POST /api/v1/shipment-groups/suggestions/preview` 预览、`/apply` 确认落库
3. **批量编辑**：`PATCH /api/v1/shipments/batch-update`

运单号 `shipment_no` 唯一；`vessel_voyage` 用于与船期模块逻辑关联（不区分大小写匹配）。

## 轨迹同步

两类轨迹：

| 类型 | 存储表 | 同步入口 |
|------|--------|----------|
| 内部/WMS | internal_tracking_logs | `POST .../sync-tracking` |
| 承运商 API | carrier_tracking_logs | `POST .../sync-carrier-tracking` |

**自动同步**：Uvicorn 启动后 `tracking_sync_scheduler` 每 N 小时全量同步（默认 2 小时，仅 `IN_TRANSIT`）。配置见 [deployment.md](./deployment.md)。

同步后更新 `latest_tracking_time`、`latest_tracking_desc`、`tracking_log_count`，并可能推进 `status_code`。关键时间字段（ETD/ATD/ETA/ATA、入仓时间、预计送仓、签收时间）由 `tracking_time_writeback` 根据内部轨迹节点自动回写（签收时间冲突时需人工审批）。若转单号为空且轨迹含 `FedEx/UPS/DHL… + 合法单号`，同步写入 `tracking_number`（不覆盖已有值）。

**分组提醒联动**：本次同步中摘要或状态有变化的运单，会自动对其所在分组执行规则评估（签收期限、整组到港催款等）；响应字段 `groupAlertsEvaluated`、`groupAlertsCreated`。日志含 `[分组提醒]` 行。手动「重新计算」仍可用于全量补跑。

```bash
# 手动同步（示例：指定运单 ID 列表）
curl -X POST "http://127.0.0.1:3001/api/v1/shipments/sync-tracking" \
  -H "Content-Type: application/json" \
  -d '{"shipment_ids": ["uuid-here"]}'
```

承运商配置在根目录 `config/config.json` 的 `vendors` 数组。运单 `carrier_code` 匹配主 vendor；若主 vendor 配置了 **`fallbackVendor`** / **`fallbackVendors`**（如SENLEI → SENLEI2），同步承运商轨迹时主系统查不到轨迹会依次尝试备用系统。

更新承运商轨迹时，承运商为「整柜」的运单计入跳过，无需配置 vendor。

从港前或在途运单列表及其轨迹抽屉打开转单号官网后，列表会标出最近一次打开的运单。再次打开其他运单的官网时，标记随之切换。

**WY（wy-express）**

| 配置项 | 说明 |
|--------|------|
| `apiUrl` | 轨迹查询 `getPublicLogisticsTrackList`，POST `{"customerOrderNumberList":["运单号"]}` |
| `authorization` | 请求头鉴权 |
| `sslVerify` | 可选，`false` 跳过证书校验 |

响应 `data.trackList[].systemOrderNumber`（如 `WYNVWFPS7SS`）回写运单 `carrier_id`（承运商单号）；轨迹节点取自 `list[].childNodeList[]`。

## 异常管理

- **开启**：`POST /api/v1/shipments/exceptions/open` — 写入 `exception_code`、`exception_opened_time`，并记录 `shipment_exception_events`
- **关闭**：`POST /api/v1/shipments/exceptions/close` — 清空当前异常，保留历史事件
- **历史**：`GET /api/v1/shipments/{id}/exception-events`

前端：`ShipmentExceptionOpenModal.vue`、`ShipmentExceptionHistory.vue`。

## 船期关联

运单字段 `vessel_voyage` 与 `vessel_voyages.vessel_voyage` 精确匹配（忽略大小写）。船期页可查看某航次下关联运单：`GET /api/v1/vessel-schedules/{voyage_id}/shipments`。

「运单中心 → 提单管理」按 DPS 提单号归集运单，默认筛出包含美国运单的提单，展开后显示该提单下的全部运单。同提单有多个柜号时分柜展示，缺柜号的运单列为待核对；只有一个已知柜号时，同提单其余运单归到该柜。

列表默认显示「未全部签收」，部分签收仍留在列表并显示进度。签收筛选可切换到「已全部签收」或「全部提单」，也可与航次、查验等状态筛选组合使用。

起运港和目的港可分别筛选，也可组合。优先使用提单绑定的挂靠港，缺少挂靠时使用运单已有的港口。同一未绑定提单中，两个条件须匹配同一票运单。

主表单独显示起运港和目的港，日期列依次为预计离港、实际离港、预计到港、实际到港。

在提单详情绑定现有航次及起运港、目的港挂靠。离港和到港日期从绑定的挂靠读取，区分实际和预计。绑定仅写提单关联，单票原航次不同会在明细标记。挂靠被移除后，提单进入待核对状态。

绑定时可直接选择“新增航次”，填写至少两个挂靠并保存。返回绑定弹窗后会选中新航次。挂靠表按顺序显示到离港日期，有实际日期时优先显示，否则标注预计日期。先点起运港，再点后续挂靠作为目的港。选完两港后再点挂靠，会从起运港开始重新选择。展开挂靠行可同时核对实际和预计日期。

「船期监控」的航次下方可切换「提单／柜」和「运单」。提单／柜按提单层的绑定查询，挂靠筛选匹配该次起运或到港记录。挂靠行的提单图标可直接筛该行，点提单号能打开对应柜的运单和清关证据。提单详情点击船名航次会跳到船期监控，并定位有效的目的港挂靠。

出口和进口分别比较柜内最近查验、放行节点，展示触发运单及原始时间和描述。同阶段只有更晚的明确放行才覆盖已知时间的查验；相同时间优先保留查验。当前清关异常也参与比较，晚于历史放行或尚无时间时显示查验。原始节点随 DPS 运单或明细状态同步逐步补齐。

海运时间节点：`etd`、`eta`、`atd`、`ata` 可与船期挂靠港时间互补或覆盖。

## 到港订阅与预警

- 运单订阅：`POST/DELETE /api/v1/shipments/{id}/subscribe` → `shipment_subscriptions`
- 首页海运预警：`GET /api/v1/maritime-alerts/overview` 聚合运单/港口到港提醒

## 注意事项

- 时间格式统一 `YYYY-MM-DD HH:mm:ss`
- 批量同步大量运单时注意承运商 API 限流
- Excel 导入为 upsert 逻辑，重复运单号会更新而非 duplicate 报错（以实现为准，变更时更新本文档）
- 删除运单不会级联删除船期，仅解除 `vessel_voyage` 关联

## 相关文档

- [database.md](./database.md) — shipments 表字段
- [api.md](./api.md) — 运单 API
- [modules/shipment/README.md](./modules/shipment/README.md)
