# 运单轨迹细状态（route_status）

## 目标

DPS `params.commerceWaybillRouteInfo.status` 提供比「转运中 / 已签收」更细的节点（入库、离港、到港、交仓、轨迹签收等）。本地拆成：

| 字段 | 含义 | 更新策略 |
|------|------|----------|
| `status_code` | 粗状态 | 插入时可写；更新默认不覆盖（`onUpdate: false`） |
| `route_status` | 细状态 | 插入 + 更新均覆盖（允许回退到更早节点） |

## 粗状态规则

1. 有 `signingTime` → `DELIVERED`
2. 否则有 route `status` → `IN_TRANSIT`
3. 否则 → `UNKNOWN`

**不使用** `markVos`、`nodeDesc` 含 signed、或 `status=601` 判定粗状态签收。601 仅映射细状态 `TRACK_SIGNED`。

## 细状态映射

码表 `shipment_route_status_codes`（种子见 `db/shipment_route_status.py`），关键：

| DPS status | code | 说明 |
|------------|------|------|
| 510 | `LAST_MILE_HANDOVER` | 快递派-已交仓（≠ 签收） |
| 601 | `TRACK_SIGNED` | 轨迹签收（≠ 粗状态 DELIVERED） |

### 非关键节点：信息传递（100）

DPS `status=100`（信息传递）**不是**业务关键节点：

1. **同步不写入** `route_status`（映射返回空），避免覆盖已有关键细状态（如到港、交仓）
2. **码表**保留该行但 `is_active=0`，筛选项不出现
3. **列表状态列**若历史数据仍是 `INFO`，按无细状态处理，回退显示粗状态

## 清关异常联动

| DPS / `route_status` | 行为 |
|----------------------|------|
| `EXPORT_CUSTOMS_EXCEPTION`（206） | 自动开启异常 `EXPORT_CUSTOMS_EXCEPTION`（出口海关异常） |
| `IMPORT_CUSTOMS_EXCEPTION`（402） | 自动开启异常 `IMPORT_CUSTOMS_EXCEPTION`（进口清关异常） |
| 其他**关键**细状态 | 若当前异常为上述清关类 → **自动解除** |
| 非关键 / 无细状态 | 不动 |

约束：

- 不覆盖已有非清关人工异常（掉件、暂扣等）
- 仅清关类异常会被后续关键节点自动解除
- 实现：`services/shipment_route_status_exception.py`，在 DPS 运单同步 upsert 后调用

## 同步配置

`config/shipment_dps_sync_fields.json`：`route_status.onUpdate = true`。

## 前端

运单列表固定「状态」列：**有 `route_status` 显示细状态中文名，否则显示粗状态**；各细状态用不同色标区分（异常偏红、签收偏绿、海运段蓝紫）。筛选项仍分「状态」（粗）和「细状态」。后台码表「轨迹细状态」可维护映射（含 `dpsStatus`）。
