# 运单异常跟踪设计方案

## 背景

当前系统已经有运单、轨迹、船期预警、运单分组提醒和统计管理能力。随着 `ETD`、`ATD`、`ETA`、`ATA`、预计送仓时间、签收时间逐步从内部轨迹回写，系统可以从“事后统计”进一步升级为“过程监控”。

新的目标是：每个渠道配置一个预估运输天数，当运单在途时间接近或超过该预估天数时，系统自动定位并提醒运营跟进。第一阶段先做到渠道级别，后续扩展到单个地址、仓库或 Amazon FC 级别。

本方案关注的是单票运单的运输时效预警和异常跟进，不替代统计管理：

```text
统计管理 = 复盘分析，看整体表现
运输时效预警 = 系统自动发现可能超时的运单
人工异常 = 运营确认的问题运单，例如查验、掉件、破损、超时
跟进提醒 = 已确认异常后的周期性待办提醒
```

## 菜单归属

建议新增菜单：

```text
运单中心 / 异常跟踪
```

原因：

- 异常跟踪是运营每日处理的待办，不是纯数据分析。
- 它面向单票运单，需要查看轨迹、联系客户、跟进承运商。
- 统计管理可以展示异常率和趋势，但异常处理入口应放在运单中心。

## 设计目标

1. 支持按渠道配置预估运输天数。
2. 支持提前 N 天提醒即将超时的未签收运单。
3. 支持超过预估截止日后生成已超时或严重超时预警。
4. 支持从预警一键转为人工异常。
5. 支持签收后自动关闭时效预警和未完成跟进提醒。
6. 首版以渠道级别规则为主，后续扩展到地址、仓库、Amazon FC。
7. 预警和异常跟进结果可进入首页/顶栏通知体系，也可在异常跟踪页面集中处理。

## 核心概念

### 运输时效规则

SLA 是 Service Level Agreement，在本系统中建议面向用户展示为“运输时效规则”或“渠道预估时效”。每个渠道配置一组运输时效规则：

```text
渠道
起算节点
预估天数
提前提醒天数
严重超时天数
是否启用
```

示例：

```text
渠道：Sea Truck Amazon
起算节点：ATD
预估天数：35 天
提前提醒：3 天
严重超时：7 天
```

计算：

```text
预估截止日 = ATD + 35 天
提醒日 = 预估截止日 - 3 天
```

如果今天已经到提醒日但运单还没有签收，生成“即将超时”预警。如果今天超过截止日仍未签收，生成“已超时”预警。如果超过截止日 7 天仍未签收，升级为“严重超时”预警。

### 三层业务边界

异常跟踪不要只靠一张“异常提醒表”承载所有事情，建议分三层：

```text
运输时效预警：系统按规则自动发现风险，不一定是真异常
人工异常：运营确认需要处理的问题，写入当前异常和异常事件历史
跟进提醒：人工异常持续未关闭时，按间隔生成待办提醒
```

典型流转：

```text
系统扫描 -> 生成运输时效预警 -> 运营查看轨迹
  -> 忽略 / 标记已处理
  -> 转为人工异常 -> 进入异常跟进提醒节奏
```

这样可以避免“即将超时”直接污染运单当前异常，也避免统计管理里的异常率被风险预警放大。

### 预计送仓时间优先

渠道预估天数是默认规则，某票运单已有预计送仓时间时，应优先使用预计送仓时间。

优先级：

```text
有 expected_delivery_time:
  预估截止日 = expected_delivery_time

没有 expected_delivery_time 且有 ATD:
  预估截止日 = ATD + 渠道预估天数

没有 expected_delivery_time 且没有 ATD:
  首版跳过全程超时扫描
```

原因：

- `expected_delivery_time` 是该票货物的具体预约/预计送仓时间，比渠道平均时效更准确。
- 渠道预估天数适合在没有具体预计送仓时间时作为兜底。

## 预警状态

运输时效预警需要区分“风险等级”和“处理状态”，不要把两者混在一个字段里。

风险等级：

| 状态 | 展示文案 | 含义 |
| --- | --- | --- |
| `warning_soon` | 即将超时 | 当前日期已到提醒日，但未超过截止日 |
| `overdue` | 已超时 | 当前日期已超过截止日 |
| `severe_overdue` | 严重超时 | 超过截止日达到严重超时天数 |

处理状态：

| 状态 | 展示文案 | 含义 |
| --- | --- | --- |
| `open` | 待处理 | 系统生成后尚未处理 |
| `acknowledged` | 已处理 | 运营已确认并处理，但未转人工异常 |
| `converted` | 已转异常 | 已转为人工异常，后续由异常跟进承接 |
| `resolved` | 已解决 | 运单已签收或系统判断不再命中 |
| `ignored` | 已忽略 | 人工确认无需继续提醒 |

风险等级升级：

```text
warning_soon -> overdue -> severe_overdue
```

签收后处理状态自动进入：

```text
resolved
```

### 当前系统异常状态

现有系统的异常状态继续作为“人工异常类型”独立存在，不和运输时效预警的 `risk_level` / `status` 混用。

```text
shipments.exception_code = 当前人工异常类型
shipment_exception_codes = 人工异常类型码表
shipment_exception_events = 人工异常开关历史
```

人工异常类型用于表达运营已经确认的问题，例如：

```text
查验中
掉件
暂扣
破损
运输超时
```

其中“运输超时”可以作为运输时效预警转人工异常时的默认异常类型。即将超时、已超时、严重超时仍属于系统预警风险等级，不直接写入 `shipments.exception_code`。

## 起算节点

规则需要保留起算节点配置，便于不同渠道适配不同业务：

| 起算节点 | 字段 | 适用场景 |
| --- | --- | --- |
| `ATD` | `atd` | 海运、卡派全程时效，首版推荐 |
| `ETD` | `etd` | 预配阶段提前监控 |
| `ATA` | `ata` | 到港后送仓时效 |
| `expected_delivery_time` | `expected_delivery_time` | 已预约送仓后的跟进 |
| `created_time` | `created_time` | 没有船期节点的快递/空运兜底 |

首版建议只实现：

```text
ATD -> signed_time
```

也就是：有 `ATD` 且未签收的运单，按渠道预估天数检查全程超时。

## 数据模型建议

### 1. channel_sla_rules

渠道预估时效规则表。`SLA` 是技术命名，页面上建议展示为“运输时效规则”。

```sql
CREATE TABLE channel_sla_rules (
    id TEXT PRIMARY KEY,
    channel_code TEXT NOT NULL,
    carrier_code TEXT NOT NULL DEFAULT '',
    start_field TEXT NOT NULL DEFAULT 'ATD',
    estimated_days INTEGER NOT NULL,
    warning_days INTEGER NOT NULL DEFAULT 3,
    severe_overdue_days INTEGER NOT NULL DEFAULT 7,
    enabled INTEGER NOT NULL DEFAULT 1,
    note TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    UNIQUE(channel_code, carrier_code, start_field)
);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `channel_code` | 渠道代码 |
| `carrier_code` | 承运商代码，空字符串表示渠道通用规则 |
| `start_field` | 起算字段，例如 `ATD` |
| `estimated_days` | 预估运输天数 |
| `warning_days` | 提前提醒天数 |
| `severe_overdue_days` | 超过截止日多少天后升级严重超时 |
| `enabled` | 是否启用 |

首版可以只配置 `channel_code`，`carrier_code` 保留为空，后续再启用承运商细分。

## 配置方式

### 配置入口

首版建议放在：

```text
系统管理 / 渠道管理 / 渠道时效配置
```

或者在 `渠道管理` 的渠道详情中增加一个配置区：

```text
渠道基础信息
运输时效规则
异常提醒规则
```

不建议把运输时效规则配置放在 `异常跟踪` 页面里。异常跟踪是处理待办，规则配置放在系统管理或渠道管理下更清晰。

### 首版配置字段

每个渠道至少配置一条默认规则：

| 配置项 | 示例 | 说明 |
| --- | --- | --- |
| 渠道 | `Sea Truck Amazon` | 选择已有渠道 |
| 起算节点 | `ATD` | 首版默认实际离港时间 |
| 预估天数 | `35` | 从起算节点到签收的标准天数 |
| 提前提醒天数 | `3` | 截止日前几天生成即将超时 |
| 严重超时天数 | `7` | 超过截止日多少天升级严重超时 |
| 是否启用 | 是 | 关闭后不参与扫描 |
| 备注 | `美西卡派常规时效` | 给运营看 |

首版默认值建议：

```text
起算节点 = ATD
提前提醒天数 = 3
严重超时天数 = 7
启用 = 是
```

`预估天数` 不建议给系统默认值，需要运营按渠道维护，避免误报。

### 配置示例

```text
渠道：SEA_TRUCK_US_WEST
起算节点：ATD
预估天数：35
提前提醒天数：3
严重超时天数：7
启用：是
```

运单：

```text
ATD = 2026-06-01
signed_time = 空
expected_delivery_time = 空
```

计算：

```text
预估截止日 = 2026-06-01 + 35 天 = 2026-07-06
提醒日 = 2026-07-06 - 3 天 = 2026-07-03
```

判断：

```text
2026-07-03 至 2026-07-06：即将超时
2026-07-07 至 2026-07-13：已超时
2026-07-14 起：严重超时
```

如果该票运单已经有预计送仓时间：

```text
expected_delivery_time = 2026-07-02
```

则优先使用：

```text
预估截止日 = 2026-07-02
提醒日 = 2026-06-29
```

此时不再使用 `ATD + 35 天` 作为截止日。

### 承运商细分配置

第二阶段可以允许同一渠道按承运商覆盖：

```text
渠道：SEA_TRUCK_US_WEST
承运商：COSCO
预估天数：33

渠道：SEA_TRUCK_US_WEST
承运商：空
预估天数：35
```

匹配优先级：

```text
渠道 + 承运商
> 渠道默认
```

如果运单渠道是 `SEA_TRUCK_US_WEST` 且承运商是 `COSCO`，使用 33 天；如果没有承运商专属规则，使用渠道默认 35 天。

### 地址级配置预留

后续扩展到单个地址、仓库或 Amazon FC 时，可以增加更细规则：

| 配置项 | 示例 |
| --- | --- |
| 渠道 | `SEA_TRUCK_US_WEST` |
| 地址类型 | `Amazon FC` |
| 地址/仓库代码 | `ONT8` |
| 预估天数 | `38` |
| 提前提醒天数 | `3` |

匹配优先级见下方“规则匹配优先级”。

### 2. shipment_sla_alerts

运输时效预警表。它只记录系统按运输时效规则自动发现的风险，不直接替代 `shipments.exception_code` 和 `shipment_exception_events`。

```sql
CREATE TABLE shipment_sla_alerts (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL,
    alert_type TEXT NOT NULL DEFAULT 'DELIVERY_TIME',
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning',
    rule_id TEXT NOT NULL DEFAULT '',
    rule_scope TEXT NOT NULL DEFAULT 'channel',
    channel_code TEXT NOT NULL DEFAULT '',
    carrier_code TEXT NOT NULL DEFAULT '',
    start_field TEXT NOT NULL DEFAULT '',
    start_time TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL,
    warning_date TEXT NOT NULL DEFAULT '',
    converted_exception_code TEXT NOT NULL DEFAULT '',
    converted_event_id TEXT NOT NULL DEFAULT '',
    acknowledged_time TEXT NOT NULL DEFAULT '',
    resolved_time TEXT NOT NULL DEFAULT '',
    ignored_time TEXT NOT NULL DEFAULT '',
    owner TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    event_key TEXT NOT NULL UNIQUE,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `alert_type` | 预警类型，首版可用 `DELIVERY_TIME` |
| `risk_level` | `warning_soon`、`overdue`、`severe_overdue` |
| `status` | `open`、`acknowledged`、`converted`、`resolved`、`ignored` |
| `severity` | `info`、`warning`、`urgent` |
| `rule_id` | 命中的运输时效规则 |
| `rule_scope` | 规则来源，例如 `channel`、`carrier_channel`、`address` |
| `start_time` | 起算时间 |
| `due_date` | 预估截止日 |
| `warning_date` | 提醒日 |
| `converted_exception_code` | 转为人工异常时写入的异常类型 |
| `converted_event_id` | 转为人工异常后对应的异常事件 ID |
| `event_key` | 防重复键 |

`event_key` 建议：

```text
shipment_id + alert_type + rule_id + due_date
```

### 3. shipment_exception_followup_notifications

人工异常后的周期跟进提醒已经有独立表承接，首版不需要重复新建：

```text
shipment_exception_followup_notifications
```

它的职责是：当运单已经存在当前异常，且异常持续超过跟进间隔时，生成待办通知。运输时效预警转为人工异常后，再进入这个提醒节奏。

## 规则匹配优先级

第一阶段只需要渠道级：

```text
channel_code
```

后续扩展到地址级时，建议按以下优先级匹配：

```text
单个地址规则
> 渠道 + 地址规则
> 渠道 + Amazon FC / 仓库规则
> 渠道 + 目的港规则
> 渠道 + 承运商规则
> 渠道规则
```

示例：

```text
渠道 A 默认 35 天
渠道 A + ONT8 仓 38 天
渠道 A + LAX9 仓 32 天
```

如果运单送往 ONT8，则使用 38 天；如果没有命中地址或仓库规则，则回退到渠道默认 35 天。

## 扫描逻辑

计划任务每天执行，也可以在轨迹时间字段回写后触发单票重算。

### 主流程

```text
加载未签收运单
  -> 找到运单匹配的运输时效规则
  -> 计算预估截止日 due_date
  -> 计算提醒日 warning_date
  -> 根据当前日期判断风险等级 risk_level
  -> 生成或更新运输时效预警
  -> 已签收运单自动关闭未解决预警
  -> 已转人工异常的预警不重复创建新预警
```

### 截止日计算

```text
如果有 expected_delivery_time:
  due_date = expected_delivery_time
  rule_scope = expected_delivery_time

否则:
  start_time = shipment[start_field]
  due_date = start_time + estimated_days
  rule_scope = channel
```

### 风险等级判断

```text
如果 signed_time 存在:
  status = resolved

否则如果 today > due_date + severe_overdue_days:
  risk_level = severe_overdue

否则如果 today > due_date:
  risk_level = overdue

否则如果 today >= due_date - warning_days:
  risk_level = warning_soon

否则:
  不生成提醒，或保持 normal
```

### 处理状态更新

```text
首次命中:
  status = open

运营标记已处理:
  status = acknowledged

运营转为人工异常:
  status = converted
  同时写入 shipments.exception_code 和 shipment_exception_events

运营忽略:
  status = ignored

运单签收:
  status = resolved
```

如果已经存在 `open` 或 `acknowledged` 预警，扫描时只更新 `risk_level`、`due_date`、`warning_date`、`updated_time`。如果已经是 `converted`、`ignored`、`resolved`，默认不重新打开，除非规则或截止日发生实质变化。

### 日期口径

首版按日期比较，不比较时分秒：

```text
today = date(now)
due_date = date(due_date)
```

## 页面设计

### 异常跟踪列表

字段：

```text
运单号
客户
渠道
承运商
目的港
ATD
预计送仓时间
签收时间
预估截止日
剩余/超期天数
风险等级
当前异常类型
规则来源
最后轨迹
负责人
处理状态
```

筛选：

```text
即将超时
已超时
严重超时
待处理
已处理
已转异常
已解决
已忽略
有当前异常
当前异常类型
渠道
承运商
客户
负责人
```

操作：

```text
查看运单
查看轨迹
标记已处理
转为人工异常
忽略提醒
添加备注
分配负责人
```

`转为人工异常` 建议弹出确认框，要求选择异常类型，默认可选：

```text
运输超时
```

确认后写入当前异常和异常事件历史，并把该预警状态改为 `converted`。

页面上可以把运输时效预警和当前人工异常放在同一个异常跟踪入口中，但筛选维度要分开：

```text
风险等级：即将超时 / 已超时 / 严重超时
预警处理状态：待处理 / 已处理 / 已转异常 / 已解决 / 已忽略
当前异常类型：查验中 / 掉件 / 暂扣 / 破损 / 运输超时
```

如果一票运单既有运输时效预警，又有当前人工异常，列表中同时展示两类标签。运营可以直接处理预警，也可以进入当前异常的跟进记录。

### 列表排序

默认排序：

```text
严重超时
已超时
即将超时
待处理优先于已处理
按超期天数倒序
```

## 首页与顶栏提醒

异常跟踪需要专门页面集中处理，首页和顶栏只负责提醒与跳转，不承载完整处理流程。

分工：

```text
首页 = 摘要、数量、最高优先级入口
顶栏通知 = 需要立即关注的少量待办
异常跟踪页 = 查看明细、筛选、转异常、忽略、标记处理、分配负责人
```

首页建议展示轻量摘要卡片：

```text
异常跟踪
待处理：12
严重超时：3
已超时：5
当前人工异常：4
```

点击摘要项后跳转到异常跟踪页，并带上筛选条件：

```text
/shipment-exceptions?status=open
/shipment-exceptions?riskLevel=severe_overdue
/shipment-exceptions?riskLevel=overdue&status=open
/shipment-exceptions?hasException=true
```

顶栏通知只推高优先级事项：

```text
严重超时且待处理
已超时且待处理
人工异常跟进到期
分配给当前用户的异常
```

不建议把全部“即将超时”明细推到顶栏通知，数量容易过大。即将超时适合在首页展示汇总数，并在异常跟踪页集中筛选处理。

## 与统计管理的关系

运输时效预警和人工异常都可以反哺统计管理，但统计口径要分开：

```text
统计管理展示：
- 时效预警票数
- 时效预警率
- 人工异常票数
- 人工异常率
- 按渠道异常率
- 按承运商异常率
- 按客户异常率
```

建议统计管理里把“预警”和“异常”分成两个指标，避免即将超时的风险票被误算为真实异常。

但处理入口仍在：

```text
运单中心 / 异常跟踪
```

## 与人工异常跟进的关系

当前系统已经存在人工异常和异常跟进提醒：

```text
shipments.exception_code = 当前人工异常快照
shipment_exception_events = 人工异常开关历史
shipment_exception_followup_notifications = 人工异常持续未关闭后的周期提醒
```

运输时效预警不直接覆盖这些数据。只有运营点击“转为人工异常”时，才写入当前异常和异常事件历史。

建议边界：

```text
运输时效预警：系统发现风险
人工异常：运营确认问题
异常跟进提醒：确认问题后持续催办
```

示例：

```text
某票运单即将超时 -> 生成 shipment_sla_alerts
运营查看后认为承运商已确认延误 -> 转为人工异常「运输超时」
后续如果异常持续未关闭 -> shipment_exception_followup_notifications 周期提醒
```

## 与分组提醒的关系

运单分组提醒面向一组货物的业务规则，例如首票签收后其他票的罚款期限、整组到港催款。

运输时效预警面向单票运单，例如某票运单是否快要超过渠道预估签收期限。

两者都可以进入通知体系，但规则来源不同：

```text
shipment_group_alerts = 组规则提醒
shipment_sla_alerts = 单票运输时效预警
shipment_exception_followup_notifications = 人工异常跟进提醒
```

## 首版落地范围

建议第一版实现：

1. 渠道运输时效配置：`channel_code`、`estimated_days`、`warning_days`、`severe_overdue_days`。
2. 每天计划任务扫描未签收运单。
3. 截止日优先级：
   - 有 `expected_delivery_time`：使用预计送仓时间。
   - 否则有 `ATD`：使用 `ATD + 渠道预估天数`。
   - 否则跳过。
4. 生成 `shipment_sla_alerts`，风险等级为 `warning_soon`、`overdue`、`severe_overdue`。
5. 异常跟踪页面集中处理预警，支持标记已处理、忽略、转为人工异常。
6. 转为人工异常时复用现有 `shipment_exception_events` 和当前异常字段。
7. 签收后自动关闭未解决预警，并关闭该票未完成的异常跟进提醒。
8. 新增 `运单中心 / 异常跟踪` 页面集中处理。
9. 首页增加异常跟踪摘要卡片，只展示数量和跳转入口。
10. 顶栏通知只推严重超时、已超时待处理、人工异常跟进到期、分配给当前用户的异常。

暂不强制实现：

```text
地址级规则
Amazon FC 规则
承运商 + 渠道规则
复杂审批流
自动派单负责人
自动把所有超时预警写入当前异常
在首页直接处理异常
把全部即将超时明细推到顶栏通知
```

## 后续扩展

1. 增加单个地址、Amazon FC、目的港级别运输时效规则。
2. 增加承运商 + 渠道组合规则。
3. 增加不同阶段时效规则，例如到港后送仓、清关后送仓。
4. 异常关闭时要求填写处理结果，形成运营复盘数据。
5. 异常统计进入 `数据中心 / 统计管理`。
6. 对连续异常较高的渠道或承运商生成管理层提醒。
