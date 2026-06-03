# 运单域（shipment）

## 模块名称

Shipment — 运单管理域

## 功能说明

运单的录入、查询、轨迹同步、异常管理、导出导入及与船期的关联。横跨 `db/`、`services/`、`schemas/`、`frontend/`。

## 主要文件

### 后端

| 路径 | 作用 |
|------|------|
| `db/shipments_table.py` | 运单表结构 |
| `db/shipments_repository.py` | 列表/CRUD/筛选 |
| `db/shipment_exception_events_*` | 异常事件 |
| `db/shipment_tracking_numbers_*` | 多跟踪号 |
| `db/shipment_subscriptions_table.py` | 到港订阅 |
| `services/shipment_excel.py` | Excel |
| `services/tracking_sync.py` | 同步 |
| `schemas/shipments.py` | API 模型 |

### 前端

| 路径 | 作用 |
|------|------|
| `views/shipments/ShipmentsView.vue` | 主列表页 |
| `components/shipments/*` | 表单、轨迹抽屉、异常 UI |
| `api/shipments.ts` | API 客户端 |

## 数据结构

主表 `shipments`，字段见 [database.md](../../database.md#shipments运单主表)。

## API 接口

前缀 `/api/v1/shipments`，详见 [api.md](../../api.md#运单-shipments)。

## 业务流程

见 [shipment-flow.md](../../shipment-flow.md)。

## 注意事项

- `shipment_no` 唯一
- `vessel_voyage` 与船期模块逻辑关联
- 轨迹同步默认仅处理 `IN_TRANSIT`
- 承运商配置在根 `config/config.json`
