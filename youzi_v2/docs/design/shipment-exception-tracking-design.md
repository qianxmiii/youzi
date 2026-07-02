# 运单异常跟踪设计方案

## 背景

当前系统已经有运单、轨迹、船期预警、运单分组提醒和统计管理能力。随着 `ETD`、`ATD`、`ETA`、`ATA`、预计送仓时间、签收时间逐步从内部轨迹回写，系统可以从“事后统计”进一步升级为“过程监控”。

新的目标是：每个渠道配置一个预估运输天数，当运单在途时间接近或超过该预估天数时，系统自动定位并提醒运营跟进。第一阶段先做到渠道级别，后续扩展到单个地址、仓库或 Amazon FC 级别。

本方案关注的是单票运单的异常跟踪，不替代统计管理：

```text
统计管理 = 复盘分析，看整体表现
异常跟踪 = 过程监控，提前发现可能超时的运单
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
3. 支持超过预估截止日后生成已超时异常。
4. 支持签收后自动关闭异常。
5. 首版以渠道级别规则为主，后续扩展到地址、仓库、Amazon FC。
6. 异常结果可进入首页/顶栏通知体系，也可在异常跟踪页面集中处理。

## 核心概念

### 渠道预估时效

每个渠道配置一组 SLA 规则：

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

如果今天已经到提醒日但运单还没有签收，生成“即将超时”。如果今天超过截止日仍未签收，生成“已超时”。如果超过截止日 7 天仍未签收，升级为“严重超时”。

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

## 异常状态

推荐状态：

| 状态 | 展示文案 | 含义 |
| --- | --- | --- |
| `normal` | 正常 | 未达到提醒条件 |
| `warning_soon` | 即将超时 | 当前日期已到提醒日，但未超过截止日 |
| `overdue` | 已超时 | 当前日期已超过截止日 |
| `severe_overdue` | 严重超时 | 超过截止日达到严重超时天数 |
| `resolved` | 已解决 | 运单已签收或人工关闭 |
| `ignored` | 已忽略 | 人工确认无需继续提醒 |

状态升级：

```text
normal -> warning_soon -> overdue -> severe_overdue -> resolved
```

签收后自动进入：

```text
resolved
```

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

渠道预估时效规则表。

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
渠道时效 SLA
异常提醒规则
```

不建议把 SLA 配置放在 `异常跟踪` 页面里。异常跟踪是处理待办，渠道 SLA 是规则配置，放在系统管理或渠道管理下更清晰。

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

### 2. shipment_exception_alerts

异常提醒表。

```sql
CREATE TABLE shipment_exception_alerts (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL,
    alert_type TEXT NOT NULL,
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
| `alert_type` | 异常类型，首版可用 `DELIVERY_SLA` |
| `status` | `warning_soon`、`overdue`、`severe_overdue`、`resolved`、`ignored` |
| `severity` | `info`、`warning`、`urgent` |
| `rule_id` | 命中的 SLA 规则 |
| `rule_scope` | 规则来源，例如 `channel`、`carrier_channel`、`address` |
| `start_time` | 起算时间 |
| `due_date` | 预估截止日 |
| `warning_date` | 提醒日 |
| `event_key` | 防重复键 |

`event_key` 建议：

```text
shipment_id + alert_type + rule_id + due_date
```

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
  -> 找到运单匹配的 SLA 规则
  -> 计算预估截止日 due_date
  -> 计算提醒日 warning_date
  -> 根据当前日期判断异常状态
  -> 生成或更新异常提醒
  -> 已签收运单自动关闭未解决异常
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

### 状态判断

```text
如果 signed_time 存在:
  status = resolved

否则如果 today > due_date + severe_overdue_days:
  status = severe_overdue

否则如果 today > due_date:
  status = overdue

否则如果 today >= due_date - warning_days:
  status = warning_soon

否则:
  不生成提醒，或保持 normal
```

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
异常等级
规则来源
最后轨迹
负责人
状态
```

筛选：

```text
即将超时
已超时
严重超时
已解决
已忽略
渠道
承运商
客户
负责人
```

操作：

```text
查看运单
标记已处理
忽略提醒
添加备注
分配负责人
```

### 列表排序

默认排序：

```text
严重超时
已超时
即将超时
按超期天数倒序
```

## 与统计管理的关系

异常跟踪产生的结果可以反哺统计管理：

```text
统计管理展示：
- 异常票数
- 异常率
- 按渠道异常率
- 按承运商异常率
- 按客户异常率
```

但处理入口仍在：

```text
运单中心 / 异常跟踪
```

## 与分组提醒的关系

运单分组提醒面向一组货物的业务规则，例如首票签收后其他票的罚款期限、整组到港催款。

异常跟踪面向单票运单的时效 SLA，例如某票运单是否快要超过渠道预估签收期限。

两者都可以进入通知体系，但规则来源不同：

```text
shipment_group_alerts = 组规则提醒
shipment_exception_alerts = 单票异常跟踪
```

## 首版落地范围

建议第一版实现：

1. 渠道 SLA 配置：`channel_code`、`estimated_days`、`warning_days`、`severe_overdue_days`。
2. 每天计划任务扫描未签收运单。
3. 截止日优先级：
   - 有 `expected_delivery_time`：使用预计送仓时间。
   - 否则有 `ATD`：使用 `ATD + 渠道预估天数`。
   - 否则跳过。
4. 生成 `warning_soon`、`overdue`、`severe_overdue`。
5. 签收后自动关闭异常。
6. 新增 `运单中心 / 异常跟踪` 页面集中处理。

暂不强制实现：

```text
地址级规则
Amazon FC 规则
承运商 + 渠道规则
复杂审批流
自动派单负责人
```

## 后续扩展

1. 增加单个地址、Amazon FC、目的港级别 SLA。
2. 增加承运商 + 渠道组合规则。
3. 增加不同阶段 SLA，例如到港后送仓、清关后送仓。
4. 异常关闭时要求填写处理结果，形成运营复盘数据。
5. 异常统计进入 `数据中心 / 统计管理`。
6. 对连续异常较高的渠道或承运商生成管理层提醒。
