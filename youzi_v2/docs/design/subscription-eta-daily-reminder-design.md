# 订阅运单 · ETA 到港前每日提醒

**状态**：已确认（方案 A）  
**日期**：2026-08-05

## 目标

运单列表点击「订阅」后，除轨迹更新通知外：在 **ETA 前 7 天起至签收前**，每天向 **顶栏消息铃铛** 推送一条提醒。

## 规则

| 项 | 约定 |
|----|------|
| 范围 | `shipment_subscriptions` 已订阅 |
| 日期 | 使用运单 `eta`（取日期部分） |
| 开始 | `today >= eta_date - 7` |
| 结束 | 已签收（`status_code=DELIVERED` 或 `delivered_time` 非空）则不再提醒 |
| 频率 | 每运单每天最多 1 条（按本地日历日去重） |
| 通道 | 复用表 `shipment_arrival_notifications`，`tracking_source=eta_reminder` |

## 实现要点

1. `shipment_subscriptions` 增加 `last_notified_eta_day`（TEXT，`YYYY-MM-DD`）防同日重复。
2. `ShipmentSubscriptionsRepository.evaluate_eta_reminders()`：扫描订阅运单并写通知。
3. `tracking_sync_scheduler` 周期 tick 中调用（按日去重，可每小时扫）。
4. 顶栏消息铃铛对 `eta_reminder` 展示中文文案（距 ETA 天数 / 今日预计到港 / 已过 ETA 未签收）。

## 非目标

- 不进待办清单。
- 不以 ATA 作为停止条件（仅签收停止）。
- 不新建独立提醒表。
