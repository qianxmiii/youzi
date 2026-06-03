# API 文档

## 目录

- [概述](#概述)
- [通用约定](#通用约定)
- [健康检查](#健康检查)
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

## 运单 shipments

前缀：`/api/v1/shipments`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 列表（筛选、分页） |
| GET | `/{item_id}` | 单条详情 |
| POST | `/` | 新建 |
| PUT | `/{item_id}` | 更新 |
| DELETE | `/{item_id}` | 删除 |
| POST | `/batch-delete` | 批量删除 |
| PATCH | `/batch-update` | 批量更新 |
| GET | `/filter-options` | 筛选项 |
| GET | `/export` | Excel 导出 |
| POST | `/import` | Excel 导入 |
| POST | `/sync-tracking` | 同步内部轨迹 |
| POST | `/sync-carrier-tracking` | 同步承运商轨迹 |
| GET | `/tracking-freshness-stats` | 轨迹新鲜度统计 |
| GET | `/tracking-sync/daily-stats` | 日同步统计 |
| POST | `/exceptions/open` | 开启异常 |
| POST | `/exceptions/close` | 关闭异常 |
| GET | `/{item_id}/exception-events` | 异常历史 |
| GET | `/{item_id}/tracking-logs` | 内部轨迹 |
| GET | `/{item_id}/carrier-tracking-logs` | 承运商轨迹 |
| POST | `/{item_id}/subscribe` | 订阅轨迹更新提醒 |
| DELETE | `/{item_id}/subscribe` | 取消订阅 |
| POST | `/batch-subscribe` | 批量订阅 |
| POST | `/batch-unsubscribe` | 批量取消订阅 |

**订阅消息（顶栏铃铛）**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/shipment-subscriptions/notifications` | 未读通知列表与 `unreadCount` |
| POST | `/api/v1/shipment-subscriptions/notifications/read-all` | 全部标为已读 |
| POST | `/api/v1/maritime-alerts/shipment-arrivals/{id}/read` | 单条标为已读 |

**列表示例**

```bash
curl "http://127.0.0.1:3001/api/v1/shipments?page=1&page_size=20&status_code=IN_TRANSIT"
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
| GET | `/api/v1/maritime-alerts/overview` | 首页预警概览 |
| POST | `/api/v1/maritime-alerts/port-arrivals/{id}/read` | 标记港口到港已读 |
| POST | `/api/v1/maritime-alerts/shipment-arrivals/{id}/read` | 标记运单到港已读 |
| POST | `/api/v1/maritime-alerts/notifications/read-all` | 全部已读 |

## 客户与渠道

| 前缀 | 说明 |
|------|------|
| `/api/v1/customers` | CRUD + `sync-from-shipments` |
| `/api/v1/channels` | CRUD + `seed-defaults`、`/meta` |

## 统计与计划任务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/statistics/shipments/overview` | 运单统计概览 |
| GET | `/api/v1/scheduled-tasks/overview` | 计划任务概览 |
| PUT | `/api/v1/scheduled-tasks/settings` | 更新同步配置 |
| GET | `/api/v1/scheduled-tasks/jobs` | 同步任务历史 |
| POST | `/api/v1/scheduled-tasks/run-*-sync` | 手动触发同步 |

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
