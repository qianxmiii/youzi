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

运单（Shipment）是 Youzi v2 的核心业务对象，贯穿录入、在途跟踪、异常处理、海运节点与签收。前端入口：`/shipments`（`ShipmentsView.vue`）。

## 生命周期

```text
创建/导入 → 待发货/在途(IN_TRANSIT) → 轨迹更新 → 签收(delivered_time)
                ↓
            异常开启 → 处理 → 异常关闭
```

状态码存储在 `shipments.status_code`，具体枚举见码表 `shipment_status`（`db/code_tables.py`）。

## 数据录入

三种方式：

1. **单条表单**：`POST /api/v1/shipments`（`ShipmentFormModal.vue`）
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

同步后更新 `latest_tracking_time`、`latest_tracking_desc`、`tracking_log_count`，并可能推进 `status_code`（含写入 `delivered_time`）。

**分组提醒联动**：本次同步中摘要或状态有变化的运单，会自动对其所在分组执行规则评估（签收期限、整组到港催款等）；响应字段 `groupAlertsEvaluated`、`groupAlertsCreated`。日志含 `[分组提醒]` 行。手动「重新计算」仍可用于全量补跑。

```bash
# 手动同步（示例：指定运单 ID 列表）
curl -X POST "http://127.0.0.1:3001/api/v1/shipments/sync-tracking" \
  -H "Content-Type: application/json" \
  -d '{"shipment_ids": ["uuid-here"]}'
```

承运商配置在根目录 `config/config.json` 的 `vendors` 数组。

## 异常管理

- **开启**：`POST /api/v1/shipments/exceptions/open` — 写入 `exception_code`、`exception_opened_time`，并记录 `shipment_exception_events`
- **关闭**：`POST /api/v1/shipments/exceptions/close` — 清空当前异常，保留历史事件
- **历史**：`GET /api/v1/shipments/{id}/exception-events`

前端：`ShipmentExceptionOpenModal.vue`、`ShipmentExceptionHistory.vue`。

## 船期关联

运单字段 `vessel_voyage` 与 `vessel_voyages.vessel_voyage` 精确匹配（忽略大小写）。船期页可查看某航次下关联运单：`GET /api/v1/vessel-schedules/{voyage_id}/shipments`。

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
