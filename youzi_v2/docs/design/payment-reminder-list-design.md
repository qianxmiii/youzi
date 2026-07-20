# 催款列表设计方案

## 背景

当前运单表 `shipments` 已经有付款状态字段 `payment_status`，用于标记运单是否已付款。第一版催款功能不做完整账款模块，但需要记录每次催款跟进和催款备注，先解决两个核心问题：

```text
每天打开系统时，能看到哪些未付款运单已经到了该提醒客户付款的节点。
每催款一次，都能在系统里留下一条跟进记录，方便回看沟通历史。
```

因此本方案采用“客户结算方式 + 运单时间节点 + 催款列表 + 催款跟进记录”的轻量设计。

## 菜单归属

### 客户管理

客户结算方式属于客户基础资料，应放在客户管理中维护。

建议在客户管理列表和编辑表单中增加：

```text
结算方式
月结日
```

### 运单管理 / 催款列表

催款列表是日常业务处理入口，应放在运单管理下。

```text
运单管理 / 催款列表
```

原因：

1. 催款操作面向运单，而不是单纯维护客户资料。
2. 日常用户打开页面后需要直接看到待催款明细。
3. 后续如果扩展应收金额、催款记录、客户对账，可以自然升级为应收模块。

## 首版范围

第一版做催款列表、催款跟进记录和标记已付款。

实现内容：

1. 客户管理维护结算方式。
2. 催款列表按结算方式和运单时间字段计算应催日期。
3. 默认显示已到提醒时间且未付款的运单。
4. 支持筛选全部未付款、提前 7 天提醒、当天提醒、已逾期、未设置结算方式。
5. 支持单票或批量标记已跟进，每次跟进写入一条记录。
6. 支持填写催款备注。
7. 支持单票或批量标记已付款。

暂不实现：

```text
应收金额 / 已收金额 / 余额
客户对账单
自动通知
```

## 数据模型

### customers

在 `customers` 表增加客户结算配置字段。

```sql
ALTER TABLE customers ADD COLUMN settlement_method TEXT;
ALTER TABLE customers ADD COLUMN settlement_day INTEGER;
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `settlement_method` | 客户结算方式 |
| `settlement_day` | 月结日，仅 `MONTHLY` 使用，取值 1-31 |

`settlement_method` 建议值：

| 值 | 页面文案 | 判断口径 |
| --- | --- | --- |
| `BEFORE_SHIPMENT` | 发货前结 | ETD |
| `BEFORE_ARRIVAL` | 到港前结 | ETA |
| `AFTER_ARRIVAL` | 到港后结 | ATA |
| `MONTHLY` | 月结 | warehouse_entry_time 归属月份 + 客户月结日 |
| `AFTER_DELIVERY` | 签收结 | delivered_time |

### shipments

继续使用现有 `payment_status` 字段。

当前可用状态：

| 值 | 页面文案 |
| --- | --- |
| `UNPAID` | 未付款 |
| `PAID` | 已付款 |

催款列表只关注未付款运单：

```text
payment_status IS NULL
OR payment_status = ''
OR payment_status != 'PAID'
```

如果后续要做更细账款状态，可以扩展为：

```text
UNPAID
PARTIAL_PAID
PAID
NO_NEED
```

但第一版不需要扩展。

### shipment_payment_followups

新增催款跟进记录表。每催款一次插入一条记录，不覆盖历史。

```sql
CREATE TABLE shipment_payment_followups (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL,
    customer TEXT NOT NULL DEFAULT '',
    settlement_method TEXT NOT NULL DEFAULT '',
    reminder_type TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL DEFAULT '',
    followup_time TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
);
```

建议索引：

```sql
CREATE INDEX idx_shipment_payment_followups_shipment_no
ON shipment_payment_followups(shipment_no);

CREATE INDEX idx_shipment_payment_followups_followup_time
ON shipment_payment_followups(followup_time DESC);

CREATE INDEX idx_shipment_payment_followups_customer
ON shipment_payment_followups(customer);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `shipment_id` | 运单 ID |
| `shipment_no` | 运单号，便于查询和导出 |
| `customer` | 催款时的客户名称快照 |
| `settlement_method` | 催款时命中的结算方式快照 |
| `reminder_type` | 催款时的提醒类型快照 |
| `due_date` | 催款时计算出的应付款日 |
| `followup_time` | 跟进时间，默认当前时间 |
| `note` | 催款备注 |
| `created_by` | 操作人，首版没有用户体系时可留空 |

催款列表展示跟进信息时，不需要在 `shipments` 冗余字段，直接按跟进表聚合：

```text
followup_count = COUNT(shipment_payment_followups.id)
last_followup_time = MAX(followup_time)
last_followup_note = 最新一条 note
```

## 催款规则

### 通用规则

催款列表只计算未付款运单。

```text
已付款运单不进入催款列表
未付款运单按客户结算方式判断
客户未设置结算方式时进入“未设置结算方式”分类
```

日期比较按天处理，不比较时分秒。

```text
today = 当前日期
reminder_date = 应提醒日期
due_date = 应付款节点日期
```

提醒类型：

| 类型 | 说明 |
| --- | --- |
| `upcoming_7_days` | 提前 7 天提醒 |
| `today` | 当天提醒 |
| `overdue` | 已逾期 |
| `monthly` | 月结 |
| `missing_rule` | 未设置结算方式 |
| `missing_date` | 缺少必要时间字段 |

### 发货前结

发货前结使用 `etd`。

```text
结算方式 = BEFORE_SHIPMENT
判断字段 = shipments.etd
提前提醒日 = etd - 7 天
应付款日 = etd
```

判断：

```text
today < etd - 7 天:
  不进入默认待催列表

etd - 7 天 <= today < etd:
  提醒类型 = upcoming_7_days

today = etd:
  提醒类型 = today

today > etd:
  提醒类型 = overdue
```

如果 `etd` 为空，进入“缺少必要时间字段”分类，不参与默认催款。

### 到港前结

到港前结使用 `eta`。

```text
结算方式 = BEFORE_ARRIVAL
判断字段 = shipments.eta
提前提醒日 = eta - 7 天
应付款日 = eta
```

判断：

```text
today < eta - 7 天:
  不进入默认待催列表

eta - 7 天 <= today < eta:
  提醒类型 = upcoming_7_days

today = eta:
  提醒类型 = today

today > eta:
  提醒类型 = overdue
```

如果已经有 `ata` 且仍未付款，也应显示为逾期。

如果 `eta` 为空，进入“缺少必要时间字段”分类。

### 到港后结

到港后结使用 `ata`。

```text
结算方式 = AFTER_ARRIVAL
判断字段 = shipments.ata
应付款日 = ata
```

判断：

```text
today < ata:
  不进入默认待催列表

today = ata:
  提醒类型 = today

today > ata:
  提醒类型 = overdue
```

如果 `ata` 为空，进入“缺少必要时间字段”分类。

### 月结

月结按入库时间 `warehouse_entry_time` 归属月份。

```text
结算方式 = MONTHLY
归属字段 = shipments.warehouse_entry_time
月结日 = customers.settlement_day
```

规则：

```text
某票运单 warehouse_entry_time 在 2026-06
客户 settlement_day = 5
则该票进入 2026-07-05 的月结催款范围
```

也就是说，月结日提醒上月入库且未付款的运单。

计算方式：

```text
入库月份 = warehouse_entry_time 所在月份
应付款日 = 入库月份的下个月 settlement_day
```

示例：

| 入库时间 | 月结日 | 应付款日 |
| --- | --- | --- |
| 2026-06-01 | 5 | 2026-07-05 |
| 2026-06-30 | 5 | 2026-07-05 |
| 2026-07-10 | 10 | 2026-08-10 |

如果某个月没有对应日期，例如月结日为 31，但下个月只有 30 天，则使用该月最后一天。

```text
2026-04 入库，月结日 31
应付款日 = 2026-05-31

2026-06 入库，月结日 31
应付款日 = 2026-07-31

2026-01 入库，月结日 31
应付款日 = 2026-02-28
```

如果 `warehouse_entry_time` 为空，进入“缺少必要时间字段”分类。

如果客户结算方式是月结但 `settlement_day` 为空，进入“未设置月结日”分类。

### 签收结

签收结使用 `delivered_time`。

```text
结算方式 = AFTER_DELIVERY
判断字段 = shipments.delivered_time
应付款日 = delivered_time
```

判断：

```text
today < delivered_time:
  不进入默认待催列表

today = delivered_time:
  提醒类型 = today

today > delivered_time:
  提醒类型 = overdue
```

如果 `delivered_time` 为空，进入“缺少必要时间字段”分类。

## 默认显示范围

催款列表默认显示“已到提醒时间且未付款”的运单。

包含：

```text
提前 7 天提醒
当天提醒
已逾期
月结已到期
未设置结算方式
```

不默认显示：

```text
未到提醒时间的未付款运单
缺少必要时间字段的运单
```

页面提供筛选后可以查看这些数据。

## 筛选设计

建议筛选项：

```text
催款范围
客户
结算方式
提醒类型
付款状态
是否缺少时间字段
搜索运单号 / 客户单号 / 货件号
```

催款范围：

| 值 | 说明 |
| --- | --- |
| `todo` | 默认，已到提醒时间且未付款 |
| `all_unpaid` | 全部未付款 |
| `upcoming_7_days` | 提前 7 天提醒 |
| `today` | 当天提醒 |
| `overdue` | 已逾期 |
| `missing_rule` | 未设置结算方式 |
| `missing_date` | 缺少必要时间字段 |

结算方式筛选：

```text
发货前结
到港前结
到港后结
月结
签收结
未设置
```

## 列表字段

建议列：

| 列 | 说明 |
| --- | --- |
| 运单号 | 默认可点击跳转运单列表；**整柜**（渠道 `FC-整柜` 或承运商整柜）时展示提单号 `bill_of_lading_no`（空则回退运单号） |
| 客户 | `shipments.customer` |
| 客户单号 | 默认 `customer_no`；**整柜**时展示柜号 `container_no` |
| 渠道 | `channel_code` / 渠道中文名 |
| 付款状态 | `payment_status` |
| 结算方式 | 来自 `customers.settlement_method` |
| 关键日期 | ETD / ETA / ATA / 入库时间 / 签收时间 |
| 应付款日 | 根据规则计算 |
| 提醒类型 | 提前 7 天 / 当天 / 已逾期 / 月结 |
| 距离/逾期天数 | 未到期显示剩余天数，逾期显示逾期天数 |
| 跟进次数 | 来自 `shipment_payment_followups` 聚合 |
| 上次跟进时间 | 最新一条 `followup_time` |
| 上次备注 | 最新一条 `note` |
| 操作 | 已跟进、标记已付款 |

月结运单的关键日期显示 `warehouse_entry_time`。

## 操作设计

第一版只需要：

```text
已跟进
批量已跟进
查看跟进记录
标记已付款
批量标记已付款
复制运单号
```

已跟进：

```text
点击“已跟进”
弹出备注输入框
用户填写催款备注
确认后插入 shipment_payment_followups 一条记录
刷新列表中的跟进次数、上次跟进时间、上次备注
```

备注可以为空，但建议页面提示填写，例如：

```text
已电话催款，客户说明本周五付款。
已微信提醒财务。
客户要求补发账单。
```

批量已跟进：

```text
选择多条运单
点击“批量已跟进”
弹出统一备注输入框
确认后每票各插入一条 shipment_payment_followups 记录
```

跟进记录：

```text
点击跟进次数或“查看记录”
打开抽屉或弹窗
按 followup_time 倒序展示该运单所有催款记录
```

标记已付款：

```text
更新 shipments.payment_status = 'PAID'
更新 shipments.updated_time
```

标记已付款后，该运单立即从默认催款列表移除。

## 后端接口建议

### 查询催款列表

```text
GET /api/v1/shipments/payment-reminders
```

参数：

| 参数 | 说明 |
| --- | --- |
| `scope` | `todo` / `all_unpaid` / `upcoming_7_days` / `today` / `overdue` / `missing_rule` / `missing_date` |
| `customer` | 客户 |
| `settlementMethod` | 结算方式 |
| `reminderType` | 提醒类型 |
| `search` | 运单号、客户单号、货件号 |
| `limit` | 分页 |
| `offset` | 分页 |

返回字段：

```json
{
  "items": [
    {
      "shipmentId": "string",
      "shipmentNo": "string",
      "customer": "string",
      "customerNo": "string",
      "billOfLadingNo": "string",
      "containerNo": "string",
      "isFcl": false,
      "channelCode": "string",
      "channelNameZh": "string",
      "paymentStatus": "UNPAID",
      "settlementMethod": "BEFORE_SHIPMENT",
      "settlementMethodLabel": "发货前结",
      "baseDateField": "etd",
      "baseDate": "2026-07-20",
      "dueDate": "2026-07-20",
      "reminderDate": "2026-07-13",
      "reminderType": "upcoming_7_days",
      "reminderTypeLabel": "提前7天",
      "daysUntilDue": 7,
      "overdueDays": 0,
      "followupCount": 2,
      "lastFollowupTime": "2026-07-11 10:30:00",
      "lastFollowupNote": "已微信提醒财务，本周五付款"
    }
  ],
  "total": 0
}
```

### 新增催款跟进

```text
POST /api/v1/shipments/payment-reminders/{shipment_id}/followups
```

请求：

```json
{
  "note": "已电话催款，客户说明本周五付款。"
}
```

返回：

```json
{
  "id": "string",
  "shipmentId": "string",
  "shipmentNo": "string",
  "followupTime": "2026-07-11 10:30:00",
  "note": "已电话催款，客户说明本周五付款。"
}
```

后端在写入时根据当前催款列表规则补齐快照字段：

```text
customer
settlement_method
reminder_type
due_date
```

### 批量新增催款跟进

```text
POST /api/v1/shipments/payment-reminders/followups/batch
```

请求：

```json
{
  "shipmentIds": ["..."],
  "note": "已统一发送催款消息。"
}
```

返回：

```json
{
  "total": 10,
  "created": 10,
  "failed": 0,
  "errors": []
}
```

### 查询单票催款跟进记录

```text
GET /api/v1/shipments/payment-reminders/{shipment_id}/followups
```

返回：

```json
{
  "items": [
    {
      "id": "string",
      "shipmentId": "string",
      "shipmentNo": "string",
      "customer": "string",
      "settlementMethod": "BEFORE_SHIPMENT",
      "reminderType": "overdue",
      "dueDate": "2026-07-10",
      "followupTime": "2026-07-11 10:30:00",
      "note": "已电话催款。",
      "createdBy": ""
    }
  ]
}
```

### 标记已付款

```text
POST /api/v1/shipments/{id}/mark-paid
```

或复用现有运单更新接口：

```text
PUT /api/v1/shipments/{id}
body: { "paymentStatus": "PAID" }
```

如果需要批量操作：

```text
POST /api/v1/shipments/batch
body:
{
  "ids": ["..."],
  "updates": {
    "paymentStatus": "PAID"
  }
}
```

## 前端页面建议

页面路径：

```text
/shipments/payment-reminders
```

侧边栏：

```text
运单管理
  - 运单列表
  - 异常跟进
  - 催款列表
```

页面结构：

```text
标题：催款列表
筛选栏：范围、结算方式、客户、提醒类型、搜索
表格：待催款运单
底部：分页
批量选择栏：复制运单号、批量已跟进、批量标记已付款
跟进记录弹窗/抽屉：展示单票催款历史
```

默认排序：

```text
已逾期优先
当天提醒其次
提前 7 天提醒再次
未设置结算方式最后
同一类型内按应付款日升序
```

## 客户管理改造

客户列表增加列：

```text
结算方式
月结日
```

客户编辑弹窗增加字段：

```text
结算方式：下拉选择
月结日：数字输入，仅月结时启用
```

交互规则：

```text
选择月结时，月结日必填
选择非月结时，月结日可为空
月结日限制 1-31
```

## 边界情况

### 客户不存在

如果 `shipments.customer` 在 `customers` 中找不到匹配客户：

```text
settlement_method = null
提醒类型 = missing_rule
页面显示：未维护客户
```

### 客户未设置结算方式

进入“未设置结算方式”分类。

这类运单默认显示，方便运营补齐客户资料。

### 缺少必要时间字段

例如发货前结缺少 `etd`，月结缺少 `warehouse_entry_time`。

默认不显示在待催列表，但可以通过“缺少必要时间字段”筛选查看。

### 月结日超出月份天数

使用目标月份最后一天。

例如：

```text
月结日 = 31
目标月份 = 2026-02
应付款日 = 2026-02-28
```

## 后续扩展

后续可以分阶段增加：

1. 催款人接入真实用户体系。
2. 应收金额、已收金额、未收余额。
3. 客户对账单。
4. 月结批量对账视图。
5. 首页待催款数量提醒（侧栏与催款页标题统计已落地；铃铛待办仍可扩展）。
6. 顶部通知铃铛提醒逾期催款。
7. 自动生成催款消息模板。
8. 按客户汇总催款历史。

## 首版落地顺序

建议按以下顺序实现：

1. `customers` 增加 `settlement_method`、`settlement_day`。
2. 新增 `shipment_payment_followups` 催款跟进记录表。
3. 客户管理页面支持维护结算方式和月结日。
4. 后端增加催款列表计算服务。
5. 后端增加催款列表 API。
6. 后端增加催款跟进新增、批量新增、查询记录 API。
7. 运单管理侧边栏增加“催款列表”。
8. 前端新增催款列表页面。
9. 支持单票和批量标记已跟进，保存催款备注。
10. 支持单票和批量标记已付款。
11. 补充测试：结算方式计算、月结日期、缺字段分类、跟进记录、标记已付款。
