# 报价跟进管理设计方案

## 背景

报价管理用于记录已经给客户报过价、但尚未确认是否成单的销售机会。它关注的是报价后的持续跟进，而不是运单执行。

第一版目标：

```text
记录客户 + 一批货物/地址的报价机会。
在报价有效期截止前，按每天或每 N 天提醒跟进。
每次跟进都能记录备注。
如果跟进中降价、涨价或调整报价，保留报价版本历史。
```

本方案不在第一版实现精确到每个地址/渠道/单价的明细报价，但数据结构需要为后续扩展预留空间。

## 菜单归属

新增一级或业务分组菜单：

```text
报价中心
  - 报价跟进
```

第一版只做 `报价跟进` 页面。后续可以扩展：

```text
报价中心
  - 报价跟进
  - 报价历史
  - 报价模板
  - 报价统计
```

## 核心概念

### 报价机会

报价机会表示一次客户询价或报价业务。

口径：

```text
一个客户 + 一批货物/地址 + 一个报价有效期 + 一组跟进规则
```

第一版可以用主表字段描述货物概况，例如品名、地址、箱数、重量、方数、当前报价金额、当前利润等。

### 报价版本

报价可能在跟进过程中变化，例如客户嫌贵，需要第二次降价。报价变化不能直接覆盖旧值，应新增一个报价版本。

示例：

```text
V1 初次报价：报价 1800 USD，利润 120 USD，利润率 18%
跟进记录：客户反馈价格偏高
V2 降价报价：报价 1650 USD，利润 90 USD，利润率 13%
跟进记录：已降价重新报价给客户
```

列表默认展示当前有效报价版本，历史版本可在详情中查看。

### 跟进记录

每次联系客户都记录一条跟进记录。跟进记录可以只记录沟通备注，也可以关联一次新报价版本。

```text
一次跟进可能不改报价。
一次跟进也可能产生一个新的报价版本。
```

### 后续地址单价明细

后续如果要精确到每个地址、渠道、单价，可以新增 `quote_items`，并挂到 `quote_version_id` 下。这样每个报价版本都有自己的明细，不会互相覆盖。

## 状态设计

报价机会状态：

| 值 | 页面文案 | 说明 |
| --- | --- | --- |
| `QUOTED` | 已报价 | 已给客户报价，等待跟进 |
| `FOLLOWING` | 跟进中 | 正在持续跟进 |
| `WON` | 已成单 | 客户确认成交，第一版只标记状态 |
| `LOST` | 已丢单 | 确认未成交 |
| `EXPIRED` | 已过期 | 报价有效期已过 |
| `CANCELLED` | 已取消 | 内部取消或无需继续 |

第一版页面可以简化展示为：

```text
已报价 / 跟进中 / 已成单 / 已丢单 / 已过期 / 已取消
```

参与提醒的状态：

```text
QUOTED
FOLLOWING
```

停止提醒的状态：

```text
WON
LOST
EXPIRED
CANCELLED
```

`EXPIRED` 可以由列表计算展示，也可以由定时任务批量更新。第一版建议先使用列表计算显示“已过期”，避免系统悄悄改库导致后续客户回复时不好处理。用户可以手动标记已过期，也可以延长有效期后继续跟进。

## 数据模型

### quote_opportunities

报价机会主表，保存当前状态、客户信息、跟进规则和当前有效报价摘要。

```sql
CREATE TABLE quote_opportunities (
    id TEXT PRIMARY KEY,
    quote_no TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL DEFAULT '',
    customer_name TEXT NOT NULL DEFAULT '',
    is_new_customer INTEGER NOT NULL DEFAULT 0,
    customer_inquiry_no TEXT NOT NULL DEFAULT '',
    quote_date TEXT NOT NULL,
    deadline_date TEXT NOT NULL DEFAULT '',
    followup_interval_days INTEGER NOT NULL DEFAULT 1,
    next_followup_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'QUOTED',
    owner TEXT NOT NULL DEFAULT '',

    product_name TEXT NOT NULL DEFAULT '',
    address_text TEXT NOT NULL DEFAULT '',
    ctns INTEGER,
    weight_kg REAL,
    volume_cbm REAL,

    current_quote_version_id TEXT NOT NULL DEFAULT '',
    current_quoted_amount REAL,
    current_quoted_currency TEXT NOT NULL DEFAULT '',
    current_profit_amount REAL,
    current_profit_currency TEXT NOT NULL DEFAULT '',
    current_profit_rate REAL,

    lost_reason TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    converted_shipment_id TEXT NOT NULL DEFAULT '',
    converted_shipment_no TEXT NOT NULL DEFAULT '',
    converted_time TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
);
```

建议索引：

```sql
CREATE INDEX idx_quote_opportunities_customer
ON quote_opportunities(customer_name);

CREATE INDEX idx_quote_opportunities_status
ON quote_opportunities(status);

CREATE INDEX idx_quote_opportunities_next_followup
ON quote_opportunities(next_followup_date);

CREATE INDEX idx_quote_opportunities_deadline
ON quote_opportunities(deadline_date);

CREATE INDEX idx_quote_opportunities_owner
ON quote_opportunities(owner);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `quote_no` | 系统自动生成报价编号，例如 `QT202607130001` |
| `customer_id` | 已有客户 ID，新客户可为空 |
| `customer_name` | 客户名称快照；新客户直接录入名称 |
| `is_new_customer` | 是否新客户，1 表示尚未进入客户管理 |
| `customer_inquiry_no` | 客户自己的询价编号，可空 |
| `quote_date` | 报价日期 |
| `deadline_date` | 报价有效期截止日 |
| `followup_interval_days` | 跟进间隔天数，1 表示每天 |
| `next_followup_date` | 下次跟进日期，可由系统计算，也可人工覆盖 |
| `status` | 报价机会状态 |
| `owner` | 负责人，首版可为空 |
| `product_name` | 品名，可选 |
| `address_text` | 地址或地址概况，可选 |
| `ctns` | 箱数，可选 |
| `weight_kg` | 重量 KG，可选 |
| `volume_cbm` | 方数 CBM，可选 |
| `current_quote_version_id` | 当前有效报价版本 ID |
| `current_quoted_amount` | 当前报价金额，可选 |
| `current_quoted_currency` | 当前报价币种，例如 `USD` / `CNY` |
| `current_profit_amount` | 当前预估利润金额，可选 |
| `current_profit_currency` | 当前利润币种 |
| `current_profit_rate` | 当前预估利润率，百分比，可选，不强制自动互算 |
| `lost_reason` | 丢单原因，可选 |
| `converted_shipment_id` | 后续成单关联运单预留字段，第一版不使用 |
| `converted_shipment_no` | 后续成单关联运单号预留字段，第一版不使用 |

### quote_versions

报价版本表。每次初次报价、降价、涨价、调整货物、调整地址时新增一条。

```sql
CREATE TABLE quote_versions (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    version_no INTEGER NOT NULL,
    version_time TEXT NOT NULL,
    change_reason TEXT NOT NULL DEFAULT '',

    product_name TEXT NOT NULL DEFAULT '',
    address_text TEXT NOT NULL DEFAULT '',
    ctns INTEGER,
    weight_kg REAL,
    volume_cbm REAL,

    quoted_amount REAL,
    quoted_currency TEXT NOT NULL DEFAULT '',
    profit_amount REAL,
    profit_currency TEXT NOT NULL DEFAULT '',
    profit_rate REAL,

    note TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    UNIQUE(quote_id, version_no)
);
```

建议索引：

```sql
CREATE INDEX idx_quote_versions_quote_id
ON quote_versions(quote_id, version_no DESC);
```

`change_reason` 建议值：

| 值 | 页面文案 |
| --- | --- |
| `INITIAL` | 初次报价 |
| `PRICE_DOWN` | 降价 |
| `PRICE_UP` | 涨价 |
| `CARGO_CHANGE` | 修改货物 |
| `ADDRESS_CHANGE` | 修改地址 |
| `CHANNEL_CHANGE` | 修改渠道 |
| `OTHER` | 其他 |

说明：

```text
报价版本保存历史，不删除、不覆盖。
quote_opportunities 只保存当前有效版本摘要，便于列表快速展示。
```

### quote_followups

报价跟进记录表。每跟进一次插入一条。

```sql
CREATE TABLE quote_followups (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    quote_version_id TEXT NOT NULL DEFAULT '',
    followup_time TEXT NOT NULL,
    followup_type TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    next_followup_date TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
);
```

建议索引：

```sql
CREATE INDEX idx_quote_followups_quote_id
ON quote_followups(quote_id, followup_time DESC);

CREATE INDEX idx_quote_followups_followup_time
ON quote_followups(followup_time DESC);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `quote_version_id` | 本次跟进产生或关联的报价版本，可空 |
| `followup_type` | 电话 / 微信 / 邮件 / 其他，可选 |
| `note` | 跟进备注 |
| `next_followup_date` | 本次跟进后手动指定的下次跟进日，可空 |
| `created_by` | 操作人，首版没有用户体系时可留空 |

### quote_items

第一版不实现，但预留后续扩展。用于精确记录某个报价版本下的地址、渠道、单价、利润明细。

```sql
CREATE TABLE quote_items (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    quote_version_id TEXT NOT NULL,
    address_code TEXT NOT NULL DEFAULT '',
    address_text TEXT NOT NULL DEFAULT '',
    country_code TEXT NOT NULL DEFAULT '',
    channel_code TEXT NOT NULL DEFAULT '',
    cargo_type TEXT NOT NULL DEFAULT '',
    ctns INTEGER,
    weight_kg REAL,
    volume_cbm REAL,
    unit_price REAL,
    cost_price REAL,
    quoted_amount REAL,
    quoted_currency TEXT NOT NULL DEFAULT '',
    profit_amount REAL,
    profit_currency TEXT NOT NULL DEFAULT '',
    profit_rate REAL,
    note TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
);
```

后续设计原则：

```text
quote_items 挂 quote_version_id，不直接只挂 quote_id。
每一版报价都有自己的明细。
降价或改单价时新增版本和新明细，不覆盖旧明细。
```

## 报价编号

报价编号系统自动生成。

建议格式：

```text
QTYYYYMMDDNNNN
```

示例：

```text
QT202607130001
QT202607130002
```

规则：

```text
QT + 当前日期 + 当日 4 位流水
```

客户自己的询价编号不要混入系统报价编号，单独存 `customer_inquiry_no`。

## 客户选择

新增报价时支持两种客户来源：

```text
选择已有客户
录入新客户
```

已有客户：

```text
customer_id = customers.id
customer_name = 当前客户名称快照
is_new_customer = 0
```

新客户：

```text
customer_id = ''
customer_name = 手动输入的新客户名称
is_new_customer = 1
```

页面显示：

```text
新客户标签
```

后续扩展：

```text
新客户转正式客户
绑定已有客户
```

绑定后可以更新 `customer_id`，但保留 `customer_name` 快照，避免历史显示受客户资料改名影响。

## 跟进规则

### 下次跟进日

创建报价时：

```text
如果填写 next_followup_date，使用人工填写值。
如果未填写，默认 next_followup_date = quote_date + followup_interval_days。
```

每次跟进后：

```text
如果本次跟进填写 next_followup_date，使用人工填写值。
否则 next_followup_date = followup_time 日期 + followup_interval_days。
```

如果计算出的下次跟进日超过报价有效期：

```text
不再生成普通下次跟进提醒。
页面显示即将过期或已过期。
```

### 报价有效期

`deadline_date` 表示报价有效期截止日。

判断：

```text
today <= deadline_date:
  报价仍在有效期

today > deadline_date:
  报价已过期
```

已过期后可以：

```text
标记已过期
延长有效期
标记已丢单
标记已成单
```

延长有效期后：

```text
更新 deadline_date
状态可回到 FOLLOWING
重新计算 next_followup_date
```

### 提醒范围

报价跟进页面默认显示需要处理的报价：

```text
status in (QUOTED, FOLLOWING)
AND (
  next_followup_date <= today
  OR deadline_date <= today
  OR deadline_date - today <= 3 天
)
```

筛选范围：

| 范围 | 说明 |
| --- | --- |
| `todo` | 今日待跟进 + 逾期未跟进 + 即将过期 |
| `today` | 今日待跟进 |
| `overdue_followup` | 已过跟进日但未跟进 |
| `expiring_soon` | 3 天内过期 |
| `expired` | 已过报价有效期 |
| `all_active` | 全部已报价/跟进中 |
| `won` | 已成单 |
| `lost` | 已丢单 |
| `cancelled` | 已取消 |

## 顶部待办铃铛

报价跟进可以进入顶部待办铃铛，但只显示聚合数量，不把每条报价都塞进铃铛消息。

统计范围：

```text
今日待跟进：status in (QUOTED, FOLLOWING) AND next_followup_date = today
逾期未跟进：status in (QUOTED, FOLLOWING) AND next_followup_date < today
即将过期：status in (QUOTED, FOLLOWING) AND deadline_date - today <= 3 天 AND deadline_date >= today
```

铃铛展示建议：

```text
报价跟进：今日 5，逾期 2，即将过期 1
```

点击跳转：

```text
/quote-center/followups?scope=todo
```

不进入铃铛的内容：

```text
全部报价
未到跟进日的报价
已成单报价
已丢单报价
已取消报价
普通历史报价
```

## 页面设计

### 报价跟进列表

页面路径：

```text
/quote-center/followups
```

顶部筛选：

```text
范围
状态
客户
是否新客户
负责人
报价日期范围
截止日期范围
搜索报价编号 / 客户询价编号 / 客户名称 / 品名 / 地址
```

默认列表列：

| 列 | 说明 |
| --- | --- |
| 报价编号 | `quote_no` |
| 客户 | `customer_name`，新客户显示标签 |
| 客户询价编号 | `customer_inquiry_no` |
| 状态 | `status` |
| 品名 | `product_name` |
| 地址 | `address_text` |
| 箱数 | `ctns` |
| 重量 | `weight_kg` |
| 方数 | `volume_cbm` |
| 当前报价 | `current_quoted_amount` + `current_quoted_currency` |
| 当前利润 | `current_profit_amount` + `current_profit_currency` |
| 当前利润率 | `current_profit_rate` |
| 报价日期 | `quote_date` |
| 截止日期 | `deadline_date` |
| 下次跟进 | `next_followup_date` |
| 跟进次数 | 聚合 `quote_followups` |
| 上次跟进 | 最新 `followup_time` |
| 负责人 | `owner` |
| 操作 | 已跟进、调整报价、成单、丢单、取消 |

默认排序：

```text
逾期未跟进
今日待跟进
即将过期
下次跟进日升序
截止日期升序
```

### 新增/编辑报价机会

表单字段：

```text
客户来源：已有客户 / 新客户
客户
客户询价编号
报价日期
报价有效期截止日
跟进间隔天数
下次跟进日期
负责人
品名
地址
箱数
重量 KG
方数 CBM
报价金额
报价币种
预估利润金额
利润币种
预估利润率
备注
```

保存新增报价时：

```text
生成 quote_opportunities
生成 quote_versions V1，change_reason = INITIAL
把 V1 写回 quote_opportunities.current_quote_version_id 和当前报价摘要字段
```

### 已跟进弹窗

点击 `已跟进` 打开弹窗。

字段：

```text
跟进方式
跟进备注
下次跟进日期
是否调整报价
```

如果勾选 `调整报价`，显示报价版本字段：

```text
调整原因：降价 / 涨价 / 修改货物 / 修改地址 / 修改渠道 / 其他
品名
地址
箱数
重量
方数
新报价金额
报价币种
新利润金额
利润币种
新利润率
版本备注
```

保存逻辑：

```text
如果未调整报价：
  插入 quote_followups
  更新 quote_opportunities.next_followup_date
  如果状态是 QUOTED，可更新为 FOLLOWING

如果调整报价：
  插入 quote_versions 新版本
  插入 quote_followups，并关联新版本 ID
  更新 quote_opportunities.current_quote_version_id
  更新 quote_opportunities 当前报价摘要字段
  更新 quote_opportunities.next_followup_date
  如果状态是 QUOTED，可更新为 FOLLOWING
```

### 报价详情

详情建议分为三个区域：

```text
报价机会概况
报价版本历史
跟进记录
```

报价版本历史按 `version_no DESC` 展示：

```text
V2 降价 2026-07-15
V1 初次报价 2026-07-13
```

跟进记录按 `followup_time DESC` 展示。

## 操作设计

### 标记已成单

第一版只更新状态：

```text
status = WON
停止提醒
```

预留后续字段：

```text
converted_shipment_id
converted_shipment_no
converted_time
```

后续扩展可以从已成单报价创建运单或绑定已有运单。

### 标记已丢单

操作字段：

```text
lost_reason
note
```

保存：

```text
status = LOST
停止提醒
```

`lost_reason` 第一版可用文本或固定选项：

```text
价格高
时效不合适
客户取消
竞争对手成交
客户暂无需求
其他
```

### 标记已取消

用于内部取消或误建。

```text
status = CANCELLED
停止提醒
```

### 延长有效期

当报价已过期但客户仍在沟通时：

```text
修改 deadline_date
可同步设置 next_followup_date
状态回到 FOLLOWING
```

## 后端接口建议

### 报价列表

```text
GET /api/v1/quote-opportunities
```

参数：

| 参数 | 说明 |
| --- | --- |
| `scope` | `todo` / `today` / `overdue_followup` / `expiring_soon` / `expired` / `all_active` / `won` / `lost` |
| `status` | 状态 |
| `customer` | 客户 |
| `isNewCustomer` | 是否新客户 |
| `owner` | 负责人 |
| `quoteDateFrom` / `quoteDateTo` | 报价日期范围 |
| `deadlineFrom` / `deadlineTo` | 截止日期范围 |
| `search` | 报价编号、客户询价编号、客户、品名、地址 |
| `limit` / `offset` | 分页 |

### 新增报价

```text
POST /api/v1/quote-opportunities
```

新增时同时创建 V1 报价版本。

### 更新报价

```text
PATCH /api/v1/quote-opportunities/{id}
```

用于更新基础信息、状态、有效期、负责人等。

不建议直接用它覆盖报价金额和利润。如果报价金额、利润、货物或地址发生业务变化，应创建报价版本。

### 新增跟进

```text
POST /api/v1/quote-opportunities/{id}/followups
```

请求：

```json
{
  "followupType": "wechat",
  "note": "客户反馈价格偏高，已重新核价。",
  "nextFollowupDate": "2026-07-16",
  "adjustQuote": true,
  "version": {
    "changeReason": "PRICE_DOWN",
    "quotedAmount": 1650,
    "quotedCurrency": "USD",
    "profitAmount": 90,
    "profitCurrency": "USD",
    "profitRate": 13,
    "note": "降价后重新报价"
  }
}
```

如果 `adjustQuote = false`，只新增跟进记录，不新增报价版本。

### 查询报价版本

```text
GET /api/v1/quote-opportunities/{id}/versions
```

### 查询跟进记录

```text
GET /api/v1/quote-opportunities/{id}/followups
```

### 标记状态

```text
POST /api/v1/quote-opportunities/{id}/mark-won
POST /api/v1/quote-opportunities/{id}/mark-lost
POST /api/v1/quote-opportunities/{id}/cancel
POST /api/v1/quote-opportunities/{id}/extend-deadline
```

## 首版落地范围

第一版实现：

1. 新增报价中心菜单和报价跟进页面。
2. 新增 `quote_opportunities`、`quote_versions`、`quote_followups` 表。
3. 新增报价机会时自动生成报价编号。
4. 支持选择已有客户或录入新客户，并显示新客户标签。
5. 支持报价有效期、跟进频率、下次跟进日。
6. 支持报价金额/币种、利润金额/币种、利润率。
7. 支持品名、地址、箱数、重量、方数等可选字段。
8. 支持每次跟进写备注。
9. 支持跟进时调整报价并生成新报价版本。
10. 支持标记已成单、已丢单、已取消、延长有效期。
11. 支持顶部待办铃铛聚合报价跟进数量。
12. 支持报价详情查看版本历史和跟进记录。

第一版暂不实现：

```text
quote_items 地址单价明细
从报价创建运单
报价绑定已有运单
报价单 PDF / Excel 输出
复杂权限
自动发送客户消息
报价统计报表
```

## 后续扩展

1. 增加 `quote_items`，精确到地址、渠道、单价、利润。
2. 从已成单报价创建运单或绑定已有运单。
3. 新客户转正式客户。
4. 报价单导出 PDF / Excel。
5. 报价模板和复制报价。
6. 报价转化率统计。
7. 丢单原因统计。
8. 按客户、负责人、渠道分析报价效果。
