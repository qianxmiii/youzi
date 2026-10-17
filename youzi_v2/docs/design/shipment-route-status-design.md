# 运单轨迹明细状态（route_status）

## 目标

DPS `params.commerceWaybillRouteInfo.status` 提供比「转运中 / 已签收」更细的节点（入库、离港、到港、交仓、轨迹签收等）。本地拆成：

| 字段 | 含义 | 更新策略 |
|------|------|----------|
| `status_code` | 粗状态 | 插入时可写；更新默认不覆盖（`onUpdate: false`） |
| `route_status` | 明细状态 | 插入 + 更新均覆盖（允许回退到更早节点） |

## 粗状态规则

1. 有 `signingTime` → `DELIVERED`
2. 否则有 route `status` → `IN_TRANSIT`
3. 否则 → `UNKNOWN`

**不使用** `markVos`、`nodeDesc` 含 signed、或 `status=601` 判定粗状态签收。601 仅映射明细状态 `TRACK_SIGNED`。

异常跟踪（运输时效）**待办退出**：`route_status = TRACK_SIGNED`，或粗状态 `DELIVERED` / 有 `delivered_time`。阶段卡点**起算**仍以明细节点时间为准（不由粗状态起算）。明细状态同步回写：

| 预警 / 用途 | DPS / 明细状态 | 本地时间字段 |
|-------------|----------------|--------------|
| 入库未开船 | 202 `WAREHOUSE_IN` | `route_warehouse_in_time` |
| 到港未送仓 | 306 `ARRIVED_POD` | `route_arrived_pod_time` |
| 到仓未派送 | 502 `DEST_TRANSIT_WAREHOUSE` | `route_dest_transit_warehouse_time` |
| 开船 / 到港（空则回写） | 301 `DEPARTED_POL` / 306 `ARRIVED_POD` | `atd` / `ata`（仅当库内对应字段为空时，取节点最早 `nodeTime`） |

## 明细状态映射

码表 `shipment_route_status_codes`（种子见 `db/shipment_route_status.py`），关键：

| DPS status | code | 说明 |
|------------|------|------|
| 509 | `TRUCK_DISPATCH_APPOINTED` | 卡派已约仓 |
| 510 | `LAST_MILE_HANDOVER` | 快递派-已交仓（≠ 签收） |
| 601 | `TRACK_SIGNED` | 轨迹签收（≠ 粗状态 DELIVERED） |

### 非关键节点：信息传递（100）

DPS `status=100`（信息传递）**不是**业务关键节点：

1. **同步不写入** `route_status`（映射返回空），避免覆盖已有关键明细状态（如到港、交仓）
2. **码表**保留该行但 `is_active=0`，筛选项不出现
3. **列表状态列**若历史数据仍是 `INFO`，按无明细状态处理，回退显示粗状态

## 清关异常联动

| DPS / `route_status` | 行为 |
|----------------------|------|
| `EXPORT_CUSTOMS_EXCEPTION`（206） | 自动开启异常 `EXPORT_CUSTOMS_EXCEPTION`（出口海关异常） |
| `IMPORT_CUSTOMS_EXCEPTION`（402） | 自动开启异常 `IMPORT_CUSTOMS_EXCEPTION`（进口清关异常） |
| 其他**关键**明细状态 | 若当前异常为上述清关类 → **自动解除** |
| 非关键 / 无明细状态 | 不动 |

约束：

- 不覆盖已有非清关人工异常（掉件、暂扣等）
- 仅清关类异常会被后续关键节点自动解除
- 实现：`services/shipment_route_status_exception.py`，在 DPS 运单同步 upsert 后调用

## 时效预警展示（到仓未派送细分）

预警类型仍为 `DEST_WAREHOUSE_NO_DISPATCH`（到中转仓后超时未交仓/签收）。若运单当前明细为 **509** `TRUCK_DISPATCH_APPOINTED`，列表/异常跟踪展示 **约仓未派送**（`alert_type_display_label`）。

## 轻量同步（推荐日常刷新明细状态）

- 接口完整 URL **仅**写在仓库根 `config/config.json` → `dps_route_status_query.url`（勿提交、勿写进业务代码/文档）
- 本地字段：`shipments.waybill_id` ← DPS 整单 `id`
- 后端：`POST /api/v1/shipments/sync-route-status-from-dps`（勾选或全量）；批处理：`POST /api/v1/scheduled-tasks/run-dps-route-status-sync`
- UI：运单管理「更新选中明细状态 / 更新全部明细状态」、列表状态列点击、轨迹抽屉徽章点击；计划任务「更新全部明细状态」
- **与内部轨迹**：轻量同步只写 `route_status`、阶段时间、ATD/ATA（空时）、预计送仓等；**不**覆盖 `latest_tracking_time` / `latest_tracking_desc`（列表「内部轨迹」列仍来自内部轨迹 API / `internal_tracking_logs`）
- 从节点列表按 `nodeTime` 倒序取首个**关键** `status` 写入 `route_status`，并联动清关异常
- Authorization 使用 config 根级 **`dps_authorization`**（兼容块内 `Authorization`）
- 无 `waybillId` 的单会跳过，需先「更新选中运单」补 ID

## 同步配置

`config/shipment_dps_sync_fields.json`：`route_status.onUpdate = true`（整单同步路径）。

## 前端

运单列表固定「状态」列：**有 `route_status` 显示明细状态中文名，否则显示粗状态**；各明细状态用不同色标区分（异常偏红、签收偏绿、海运段蓝紫）。**点击状态徽章**对该单调用 `sync-route-status-from-dps` 并刷新列表行（需已有 `waybillId`）。筛选项仍分「状态」（粗）和「明细状态」。后台码表「轨迹明细状态」可维护映射（含 `dpsStatus`）。

轨迹抽屉标题行：运单号右侧显示明细状态徽章（无则「无明细状态」）；**点击徽章**对该单调用 `sync-route-status-from-dps` 并刷新（需已有 `waybillId`）。下方仍保留粗状态徽章。

工作台首页「明细状态」漏斗（页头下方最上方）：口径为**未签收**；清关异常节点前置高亮；「无明细状态」含空值与信息传递。点击跳转运单管理：

| 入口 | 参数 |
|------|------|
| 某一节点 | `routeStatus={code}&notDelivered=true` |
| 无明细状态 | `missingRouteStatus=true&notDelivered=true` |
| 查看全部 | `notDelivered=true&routeStatus=_ALL`（清除默认「转运中」） |
