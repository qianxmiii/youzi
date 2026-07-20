# 业务服务（services）

## 模块名称

Youzi v2 业务服务层

## 功能说明

封装跨 Repository 的业务逻辑：轨迹同步、Excel 导入导出、承运商对接、船期抓取、海运预警等。由 `app.py` 路由层调用。

## 主要文件

| 文件 | 作用 |
|------|------|
| `tracking_sync.py` | 轨迹同步编排 |
| `tracking_sync_scheduler.py` | 定时任务调度 |
| `carrier_tracking_sync.py` | 承运商轨迹拉取 |
| `carrier_vendors.py` | 读取 config.json 承运商配置 |
| `shipment_query_config.py` | DPS 运单查询：`queryByPerson` 全量 / `queryByOrder` 按 odd，自动翻页 |
| `shipment_dps_sync.py` | DPS 运单全量同步至本地表（计划任务，默认关） |
| `shipment_dps_mapper.py` | DPS API rows → shipments 字段映射（`customer_no`：`assOrderNumber`，空则 `internalOrderNum`） |
| `shipment_dps_sync_fields.py` | 同步字段白名单（`config/shipment_dps_sync_fields.json`） |
| `logistics_tracking.py` | 物流轨迹解析 |
| `shipment_excel.py` | 运单 Excel 导入导出 |
| `payment_reminder_rules.py` | 催款结算/应催日期计算 |
| `payment_reminder_excel.py` | 催款列表 Excel 导出 |
| `vessel_schedule_excel.py` | 船期 Excel |
| `address_excel.py` | 仓库地址 Excel |
| `vessel_schedule_sync.py` | 外部船期同步 |
| `maritime_alerts.py` | 海运预警聚合 |
| `workbench_overview.py` | 工作台首页聚合（今日重点 / 待办 / 近期到港 / 运输概览） |
| `maritime_schedule/` | 船期数据源（如 COSCO eLines） |
| `port_code_resolve.py` | 港口码解析 |
| `scheduled_sync_settings.py` | 计划任务配置 |

## 业务流程

**轨迹定时同步**

```text
scheduler 触发 → 筛选 IN_TRANSIT 运单 → internal_sync + carrier_sync
              → 写日志表 → 更新 shipments 最新轨迹字段
```

**船期 Excel 导入**

```text
上传 xlsx → vessel_schedule_excel 解析 → upsert vessel_voyages + voyage_port_calls
```

## 注意事项

- 承运商 API 密钥仅通过 `carrier_vendors.py` 读 `config/config.json`
- 同步日志：`services/sync_log.py` → `youzi_v2/logs/`
- 新增承运商：实现 vendor adapter + 配置 `vendors` 数组 + 文档

## 相关文档

- [docs/shipment-flow.md](../docs/shipment-flow.md)
- [docs/deployment.md](../docs/deployment.md)
