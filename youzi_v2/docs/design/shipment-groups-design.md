# 运单分组与组提醒设计方案

## 背景

当前系统已有运单主表 `shipments`、轨迹同步、运单订阅通知、海运预警、船期和计划任务能力。新的需求是对运单进行业务分组，并基于同一组内运单状态生成提醒，例如：

- 同一批次第一票货物签收后，其他货物超过 30 天还未签收会产生罚款，需要提前一周提醒。
- 最后一批到港时提醒催款。

因此，本方案建议在现有运单体系外增加一层“运单组”，并通过组规则和组提醒事件承载后续业务扩展。

## 设计目标

1. 支持多票运单归为同一业务组。
2. 支持手动分组、批量加入分组，并为后续自动分组建议留接口。
3. 支持组级提醒规则，例如签收超时、最后一批到港催款。
4. 提醒结果可进入现有首页/顶栏通知体系。
5. 尽量复用现有 `shipments`、轨迹摘要、海运 ETA/ATA、订阅通知和计划任务机制。

## 核心模型

### 1. shipment_groups

分组主表，用来表示一批业务上有关联的运单，例如同一客户、同一订单、同一柜、同一船次或同一批货。

```sql
CREATE TABLE shipment_groups (
    id TEXT PRIMARY KEY,
    group_no TEXT NOT NULL UNIQUE,
    group_name TEXT NOT NULL DEFAULT '',
    primary_type TEXT NOT NULL DEFAULT 'MANUAL',
    customer TEXT,
    customer_no TEXT,
    vessel_voyage TEXT,
    destination_port_code TEXT,
    payment_status TEXT NOT NULL DEFAULT 'UNPAID',
    payment_due_rule TEXT NOT NULL DEFAULT 'LAST_ARRIVAL',
    note TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `group_no` | 分组编号，例如 `G20260622001` |
| `group_name` | 分组展示名称 |
| `primary_type` | 主分组类型，用于列表默认图标、排序和主标签展示 |
| `customer` / `customer_no` | 组级客户信息，便于筛选 |
| `vessel_voyage` | 组级船名航次，便于海运批次聚合 |
| `destination_port_code` | 目的港 |
| `payment_status` | 收款状态：`UNPAID`、`PARTIAL`、`PAID` |
| `payment_due_rule` | 催款触发规则，首版可用 `LAST_ARRIVAL` |

#### 分组类型

分组类型用于说明这组运单为什么被放在一起。注意：一批货物可以同时具备多个业务类型，例如既是“到港批次”，也是“收款批次”。因此不能只在 `shipment_groups` 上使用单个 `group_type` 字段。

推荐设计：

- `shipment_groups.primary_type`：主类型，只负责默认展示、排序和图标。
- `shipment_group_types`：多类型关系表，保存一组货物拥有的全部业务类型。
- 创建分组时至少选择一个类型，并从中选择一个主类型；如果用户不选，默认 `MANUAL`。
- 筛选 `groupType=PAYMENT_BATCH` 的语义是“包含该类型的分组”，不是“主类型等于该类型”。

#### shipment_group_types

```sql
CREATE TABLE shipment_group_types (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    group_type TEXT NOT NULL,
    created_time TEXT NOT NULL,
    UNIQUE(group_id, group_type)
);
```

示例：

```text
分组 G20260622001:
primary_type = PAYMENT_BATCH

shipment_group_types:
- CUSTOMER_BATCH
- PORT_BATCH
- PAYMENT_BATCH
```

这样同一批货可以同时启用签收期限提醒和到港催款提醒。

首版建议将类型做成固定枚举，后续可在系统字典中维护。

| 类型 | 名称 | 适用场景 | 建议自动匹配依据 |
| --- | --- | --- | --- |
| `MANUAL` | 手动分组 | 临时跟进、运营人工整理的任意组合 | 无，完全由用户选择 |
| `CUSTOMER_BATCH` | 客户批次 | 同一客户的一批货，需要统一跟进签收、罚款和收款 | `customer`、`customer_no` |
| `ORDER_BATCH` | 订单批次 | 同一客户订单或平台订单下的多票运单 | `customer_shipment_id`、`amazon_ref_id`、`customer_no` |
| `VESSEL_BATCH` | 船次批次 | 同一船名航次的一批海运货 | `vessel_voyage`、`vessel_name`、`voyage_no` |
| `PORT_BATCH` | 到港批次 | 同一目的港或同一 ETA 窗口内的货 | `destination_port_code`、`eta`、`ata` |
| `PAYMENT_BATCH` | 收款批次 | 以催款、账期、尾款为核心管理的一组运单 | `customer`、收款状态、人工选择 |

首版规则适用建议：

| 规则 | 默认适用分组类型 |
| --- | --- |
| `BATCH_DELIVERY_DEADLINE` | `CUSTOMER_BATCH`、`ORDER_BATCH`、`MANUAL` |
| `LAST_BATCH_ARRIVED_PAYMENT` | `VESSEL_BATCH`、`PORT_BATCH`、`PAYMENT_BATCH`、`MANUAL` |

规则启用判断必须基于 `shipment_group_types` 的多类型集合：

```text
启用 BATCH_DELIVERY_DEADLINE:
  group_types 与 {CUSTOMER_BATCH, ORDER_BATCH, MANUAL} 有交集

启用 LAST_BATCH_ARRIVED_PAYMENT:
  group_types 与 {VESSEL_BATCH, PORT_BATCH, PAYMENT_BATCH, MANUAL} 有交集
```

不要只判断 `primary_type`，否则同一批货同时需要“到港”和“催款”等多种业务视角时会漏提醒。

### 2. shipment_group_members

分组成员表。建议使用关系表，而不是只在 `shipments` 表加 `group_id`，因为后续一票运单可能同时属于“客户批次”和“船次批次”。

```sql
CREATE TABLE shipment_group_members (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'NORMAL',
    batch_no TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    UNIQUE(group_id, shipment_id)
);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `group_id` | 所属分组 |
| `shipment_id` / `shipment_no` | 关联运单 |
| `role` | 成员角色：`NORMAL`、`LAST_BATCH`、`KEY_BATCH` |
| `batch_no` | 第几批，可为空 |

### 3. shipment_group_rules

组提醒规则表。首版可以只内置固定规则，但用规则表保存开关和阈值，方便后续扩展。

```sql
CREATE TABLE shipment_group_rules (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    threshold_days INTEGER,
    warning_days INTEGER,
    trigger_status TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{}',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    UNIQUE(group_id, rule_type)
);
```

首版规则类型：

| `rule_type` | 说明 |
| --- | --- |
| `BATCH_DELIVERY_DEADLINE` | 同批次首票签收后 30 天签收期限提醒 |
| `LAST_BATCH_ARRIVED_PAYMENT` | 最后一批到港催款提醒 |

### 4. shipment_group_notifications

组提醒事件表，用于保存规则扫描后的提醒结果。

```sql
CREATE TABLE shipment_group_notifications (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning',
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    shipment_no TEXT NOT NULL DEFAULT '',
    event_key TEXT NOT NULL UNIQUE,
    triggered_at TEXT NOT NULL,
    read_at TEXT NOT NULL DEFAULT '',
    resolved_at TEXT NOT NULL DEFAULT ''
);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `rule_type` | 触发的规则类型 |
| `severity` | 提醒级别：`info`、`warning`、`urgent` |
| `shipment_no` | 某票运单触发时填写；组级触发可为空 |
| `event_key` | 防重复键，例如 `group_id + rule_type + shipment_no + date` |
| `read_at` | 已读时间 |
| `resolved_at` | 处理完成时间 |

## 规则设计

### 规则一：同批次签收不能超过 30 天

业务含义：

同一批次内，第一票货物签收后开始计算 30 天期限。其他货物如果在 30 天内仍未签收，会产生罚款风险；系统需要在到期前一周生成预警，并在超过 30 天后生成超期提醒。

首版判定建议：

1. 运单已签收条件：
   - `status_code = 'DELIVERED'`，或
   - `delivered_time` 非空。
2. 批次范围：
   - 优先使用 `shipment_group_members.batch_no` 区分同一分组下的不同批次。
   - 如果 `batch_no` 为空，则默认整个分组视为同一批次。
3. 起算时间：
   - 取同一批次内最早的签收时间作为 `first_delivered_time`。
   - 签收时间优先使用 `delivered_time`，其次可从已签收状态对应的最新轨迹时间兜底。
4. 提前提醒条件：
   - `first_delivered_time + 23 天` 后，批次内仍有未签收运单。
   - 生成“签收期限将到期”提醒，提醒距离罚款期限还有 7 天。
5. 超期提醒条件：
   - `first_delivered_time + 30 天` 后，批次内仍有未签收运单。
   - 生成“签收已超期，存在罚款风险”提醒。
6. 防重复：
   - 提前提醒使用 `event_key = group_id + batch_no + DELIVERED_DEADLINE_WARNING + first_delivered_date`。
   - 超期提醒使用 `event_key = group_id + batch_no + DELIVERED_DEADLINE_OVERDUE + first_delivered_date`。

提醒示例：

```text
签收期限将到期
分组 G20260622001 批次 B01 第一票货物已于 2026-06-01 签收，仍有 3 票未签收，距离 30 天罚款期限还有 7 天，请提前跟进。

签收已超期，存在罚款风险
分组 G20260622001 批次 B01 第一票货物已于 2026-06-01 签收，仍有 2 票超过 30 天未签收，请尽快处理。
```

### 规则二：最后一批到港时催款

业务含义：

同一组的最后一批货到港后，如果客户尚未付清款项，则生成催款提醒。

首版判定建议：

1. 最后一批识别：
   - 优先使用 `shipment_group_members.role = 'LAST_BATCH'`。
   - 如果没有人工标记最后一批，则使用组内全部运单到港作为触发条件。
2. 到港条件：
   - `ata` 非空，或
   - 海运状态已经判定为 `arrived`。
3. 催款条件：
   - `shipment_groups.payment_status != 'PAID'`。
4. 防重复：
   - 使用 `event_key = group_id + LAST_BATCH_ARRIVED_PAYMENT + arrival_date`。

提醒示例：

```text
最后一批已到港，请催款
分组 G20260622001 最后一批货已到港，当前收款状态为 UNPAID，请及时催款。
```

## 分组方式

### 1. 手动分组

在运单列表勾选多票运单，点击：

- 新建分组
- 加入已有分组
- 移出分组
- 标记为最后一批

这是首版优先实现方式，最贴合实际操作。

### 2. 自动建议分组

后续可以根据以下字段生成分组建议：

- `customer + customer_no`
- `customer + vessel_voyage`
- `customer + destination_port_code + eta`
- `amazon_ref_id`
- `customer_shipment_id`

建议先做“推荐分组”，由用户确认后落库，不建议首版自动强制分组。

### 3. Excel 导入分组

后续可在运单导入模板中增加：

- 分组编号
- 分组名称
- 批次号
- 是否最后一批

导入时按 `group_no` 自动创建或更新分组关系。

## 后端设计

建议新增模块：

```text
youzi_v2/db/shipment_groups_table.py
youzi_v2/db/shipment_groups_repository.py
youzi_v2/services/shipment_group_alerts.py
youzi_v2/routers/shipment_groups.py
youzi_v2/schemas/shipment_groups.py
```

核心服务方法：

```python
def evaluate_group_alerts(group_id: str | None = None) -> dict:
    ...
```

调用入口：

1. 计划任务定时扫描，例如每 1 小时扫描一次。
2. 运单轨迹同步后，对受影响运单所在分组即时评估。
3. 用户在分组详情页点击“重新计算提醒”。

## API 设计

建议新增接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/shipment-groups` | 分组列表，支持按 `groupType`、客户、船名航次、收款状态筛选；`groupType` 表示包含该类型 |
| `POST` | `/api/v1/shipment-groups` | 新建分组 |
| `GET` | `/api/v1/shipment-groups/{id}` | 分组详情 |
| `PUT` | `/api/v1/shipment-groups/{id}` | 更新分组 |
| `DELETE` | `/api/v1/shipment-groups/{id}` | 删除分组 |
| `POST` | `/api/v1/shipment-groups/{id}/members` | 添加成员 |
| `DELETE` | `/api/v1/shipment-groups/{id}/members` | 移除成员 |
| `PATCH` | `/api/v1/shipment-groups/{id}/members/batch` | 批量更新成员角色/批次 |
| `GET` | `/api/v1/shipment-groups/{id}/notifications` | 分组提醒列表 |
| `POST` | `/api/v1/shipment-groups/{id}/evaluate-alerts` | 手动重新计算提醒 |
| `POST` | `/api/v1/shipment-group-notifications/read-all` | 分组提醒全部已读 |

运单列表接口可扩展筛选参数：

```text
groupId
groupNo
groupType
hasGroup
```

分组创建/更新 payload 建议使用：

```json
{
  "groupName": "客户A 6月第一批",
  "primaryType": "PAYMENT_BATCH",
  "groupTypes": ["CUSTOMER_BATCH", "PORT_BATCH", "PAYMENT_BATCH"]
}
```

后端需要保证：

- `groupTypes` 至少一项。
- `primaryType` 必须包含在 `groupTypes` 中。
- 如果只传旧字段 `groupType`，可兼容转换为 `primaryType = groupType` 且 `groupTypes = [groupType]`。

## 前端设计

### 运单列表

在现有运单列表中增加：

- “分组”列，显示组名或组号。
- 分组筛选项，支持按分组类型筛选；筛选结果包含拥有该类型的分组。
- 批量操作：
  - 新建分组
  - 加入已有分组
  - 移出分组
  - 标记最后一批

### 分组管理页

新增页面 `/shipment-groups`。

页面结构：

- 左侧：分组列表和筛选，包含分组类型、客户、船名航次、收款状态。
- 右侧：分组详情。
- 详情展示：
  - 主分组类型
  - 全部分组类型标签
  - 组内运单数
  - 已到港数
  - 已签收数
  - 未签收超时数
  - 收款状态
  - 未读提醒
  - 组内运单明细

### 首页与顶栏提醒

复用现有通知风格，增加“分组提醒”来源：

- 顶栏铃铛显示未读组提醒。
- 首页海运预警区域可增加“批次提醒”面板。
- 点击提醒跳转到对应分组详情。

## 与现有模块的关系

| 现有模块 | 复用方式 |
| --- | --- |
| `shipments` | 分组成员来源，复用 `delivered_time`、`status_code`、`eta`、`ata` 等字段 |
| 轨迹同步 | 同步后触发组规则重新计算 |
| 运单订阅通知 | 可复用通知展示和已读交互思路 |
| 海运预警 | 复用到港状态判断逻辑 |
| 计划任务 | 增加组提醒扫描任务 |

## 审查结论：单 group_type 不满足业务

当前如果只实现 `shipment_groups.group_type` 单字段，会产生 P1 级设计问题：一批货物只能属于一种业务类型，无法同时表达“客户批次 + 到港批次 + 收款批次”。

具体风险：

1. 若分组类型选为 `PORT_BATCH`，签收期限规则 `BATCH_DELIVERY_DEADLINE` 可能不会启用。
2. 若分组类型选为 `CUSTOMER_BATCH`，最后一批到港催款规则 `LAST_BATCH_ARRIVED_PAYMENT` 可能不会启用。
3. 前端筛选 `groupType` 会被误实现为单值等于，而不是“包含该类型”。
4. 后续扩展规则时会继续遇到类型互斥问题。

因此实现必须调整为：

```text
shipment_groups.primary_type
shipment_group_types(group_id, group_type)
```

所有规则判断、筛选、自动建议和 Excel 导入都应基于 `shipment_group_types` 多类型集合；`primary_type` 只用于默认展示。

## 实施路线

### 阶段一：基础分组

1. 新增分组相关表。
2. 新增分组 CRUD API。
3. 支持运单批量加入/移出分组。
4. 运单列表展示分组信息并支持分组筛选。

### 阶段二：固定规则提醒

1. 实现 `BATCH_DELIVERY_DEADLINE`。
2. 实现 `LAST_BATCH_ARRIVED_PAYMENT`。
3. 新增分组提醒表和未读提醒接口。
4. 分组详情页展示提醒。

### 阶段三：通知中心接入

1. 顶栏铃铛聚合分组提醒。
2. 首页增加批次提醒区域。
3. 支持提醒已读和处理完成。

### 阶段四：自动分组建议

1. 根据客户、客户单号、船名航次、目的港等字段生成候选分组。
2. 用户确认后批量创建分组。
3. Excel 导入支持分组字段。

## 设计取舍

首版不建议做过度通用的低代码规则引擎。当前业务规则明确，使用 `rule_type + threshold_days + warning_days + config_json` 已经足够。这样既能快速落地，也能为后续扩展“预约送仓超时、清关超时、查验未解除”等规则保留空间。
