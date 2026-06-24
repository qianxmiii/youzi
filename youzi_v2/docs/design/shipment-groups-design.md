# 运单分组与组规则提醒设计方案

## 背景

当前系统已有运单主表 `shipments`、轨迹同步、运单订阅通知、海运预警、船期和计划任务能力。新的需求是对运单进行业务成组，并基于同一组内运单状态执行一组可配置规则，生成提醒，例如：

- 同一组货物中，第一票签收后，其他货物超过 30 天还未签收会产生罚款，需要提前一周提醒。
- 同一组货物全部到港后，如果客户尚未付清款项，需要提醒催款。

因此，本方案建议在现有运单体系外增加一层“运单组”。运单组只表达“这些货物属于同一组”，不再通过分组类型决定业务含义；需要执行哪些检查，由分组上配置的规则决定。

## 设计目标

1. 支持多票运单归为同一业务组。
2. 支持手动分组、批量加入分组，并为后续自动成组建议留接口。
3. 支持给同一分组配置多条组规则，例如签收超时、整组到港催款。
4. 规则结果可进入现有首页/顶栏通知体系。
5. 尽量复用现有 `shipments`、轨迹摘要、海运 ETA/ATA、订阅通知和计划任务机制。

## 核心设计原则

### 组不需要分组类型

分组只表示一批业务上需要一起跟进的货物，例如同一客户、同一订单、同一柜、同一船次或运营人工整理的一批货。系统不再维护 `group_type`、`primary_type` 或 `shipment_group_types`。

原先的“客户批次、订单批次、船次批次、到港批次、收款批次”等概念，本质上有两类用途：

1. 说明这批货为什么被放在一起。
2. 决定这批货需要执行哪些规则。

这两件事不应该绑定。首版只保留“组”与“规则”的关系：

```text
组 = 货物集合
规则 = 挂在组上的自动检查逻辑
提醒 = 规则运行后的结果
```

因此，一组货可以同时启用多条规则；规则是否执行，只取决于 `shipment_group_rules.enabled`，不再由分组类型推导。

### 规则显式配置

用户创建或编辑分组时，可以选择该分组需要启用的规则。每条规则可保存独立阈值、提醒提前量和扩展配置。

示例：

```text
分组 G20260622001:
- BATCH_DELIVERY_DEADLINE: 首票签收后 30 天期限，提前 7 天提醒
- GROUP_ARRIVED_PAYMENT: 整组货物全部到港后，如果未付清则提醒催款
- SINGLE_IN_TRANSIT_ETA_WARNING: 客户仅有一票在途时，按 ETA 提前 N 天提醒到港（默认 10 天，可改为 7 天等）
```

后续新增“预约送仓超时”“清关超时”“查验未解除”等规则时，只需要新增规则类型和执行逻辑，不需要调整分组类型体系。

## 核心模型

### 1. shipment_groups

分组主表，用来表示一批业务上有关联、需要统一跟进的运单。

```sql
CREATE TABLE shipment_groups (
    id TEXT PRIMARY KEY,
    group_no TEXT NOT NULL UNIQUE,
    group_name TEXT NOT NULL DEFAULT '',
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
| `customer` / `customer_no` | 组级客户信息，便于筛选 |
| `vessel_voyage` | 组级船名航次，便于海运批次聚合 |
| `destination_port_code` | 目的港 |
| `payment_status` | 收款状态：`UNPAID`、`PARTIAL`、`PAID` |
| `payment_due_rule` | 催款触发规则，首版可用 `LAST_ARRIVAL` |
| `note` | 运营备注 |

### 2. shipment_group_members

分组成员表。建议使用关系表，而不是只在 `shipments` 表加 `group_id`，因为后续一票运单可能同时出现在多个运营跟进组中。

```sql
CREATE TABLE shipment_group_members (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL,
    created_time TEXT NOT NULL,
    UNIQUE(group_id, shipment_id)
);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `group_id` | 所属分组 |
| `shipment_id` / `shipment_no` | 关联运单 |

### 3. shipment_group_rules

组规则配置表。每一行表示某个分组启用了一条规则。一组货可以配置多条规则，同一规则在同一分组内只能配置一次。

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

字段说明：

| 字段 | 说明 |
| --- | --- |
| `rule_type` | 规则类型 |
| `enabled` | 是否启用 |
| `threshold_days` | 规则阈值天数，例如 30 天 |
| `warning_days` | 提前提醒天数，例如提前 7 天 |
| `trigger_status` | 可选触发状态，首版可为空 |
| `config_json` | 规则扩展配置 |

首版内置规则类型：

| `rule_type` | 默认配置 | 说明 |
| --- | --- | --- |
| `BATCH_DELIVERY_DEADLINE` | `threshold_days = 30`，`warning_days = 7` | 同组首票签收后 30 天签收期限提醒 |
| `GROUP_ARRIVED_PAYMENT` | 无固定天数 | 整组到港催款提醒 |
| `SINGLE_IN_TRANSIT_ETA_WARNING` | `warning_days = 10` | 客户仅有一票在途时，按 ETA 提前 N 天提醒到港 |

规则执行判断必须基于 `shipment_group_rules`：

```text
启用某条规则:
  shipment_group_rules 中存在 group_id + rule_type
  且 enabled = 1
```

不要再通过分组类型判断规则是否启用。

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

### 规则一：同组签收不能超过 30 天

规则类型：`BATCH_DELIVERY_DEADLINE`

业务含义：

同一组货物中，第一票货物签收后开始计算签收期限。最先签收的可能是组内任意一票运单，例如运单 2 先签收，则从运单 2 的签收时间开始计算；运单 1 和运单 3 如果到提醒时间仍未签收，就需要提醒。系统不需要人工标记“第一票”或“最后一批”，只根据组内运单状态自动判断。

默认配置：

```text
threshold_days = 30
warning_days = 7
```

首版判定建议：

1. 运单已签收条件：
   - `status_code = 'DELIVERED'`，或
   - `delivered_time` 非空。
2. 规则范围：
   - 默认以整个分组作为计算范围。
   - 如果业务上存在多批货，建议创建多个分组分别跟进，而不是在同一分组内再拆子批次。
3. 起算时间：
   - 取组内最早的签收时间作为 `first_delivered_time`。
   - 签收时间优先使用 `delivered_time`，其次可从已签收状态对应的最新轨迹时间兜底。
4. 提前提醒条件：
   - `first_delivered_time + (threshold_days - warning_days) 天` 后，组内仍有未签收运单。
   - 生成“签收期限将到期”提醒。
5. 超期提醒条件：
   - `first_delivered_time + threshold_days 天` 后，组内仍有未签收运单。
   - 生成“签收已超期，存在罚款风险”提醒。
6. 防重复：
   - 提前提醒使用 `event_key = group_id + DELIVERED_DEADLINE_WARNING + first_delivered_date`。
   - 超期提醒使用 `event_key = group_id + DELIVERED_DEADLINE_OVERDUE + first_delivered_date`。

提醒示例：

```text
签收期限将到期
分组 G20260622001 第一票货物已于 2026-06-01 签收，仍有 3 票未签收，距离 30 天罚款期限还有 7 天，请提前跟进。

签收已超期，存在罚款风险
分组 G20260622001 第一票货物已于 2026-06-01 签收，仍有 2 票超过 30 天未签收，请尽快处理。
```

### 规则二：整组到港时催款

规则类型：`GROUP_ARRIVED_PAYMENT`

业务含义：

同一组货物全部到港后，如果客户尚未付清款项，则生成催款提醒。

首版判定建议：

1. 到港条件：
   - `ata` 非空，或
   - 海运状态已经判定为 `arrived`。
2. 触发条件：
   - 组内全部运单均已到港。
3. 催款条件：
   - `shipment_groups.payment_status != 'PAID'`。
4. 防重复：
   - 使用 `event_key = group_id + GROUP_ARRIVED_PAYMENT + latest_arrival_date`。

提醒示例：

```text
整组货物已到港，请催款
分组 G20260622001 组内货物已全部到港，当前收款状态为 UNPAID，请及时催款。
```

### 规则三：单票在途到港预警

规则类型：`SINGLE_IN_TRANSIT_ETA_WARNING`

业务含义：

当该客户在全库范围内**仅有一票**处于在途状态（`status_code = IN_TRANSIT`、无 ATA、未签收），且该运单在本分组内，并在 ETA 前 N 天内即将到港时，生成到港预警提醒。默认 N = 10，可在分组规则中配置为 7 天等。

首版判定建议：

1. 客户范围：分组 `customer` 字段，或从组内运单推断客户名。
2. 在途条件：全库该客户 `IN_TRANSIT` 运单**恰好 1 票**，且该票在本分组成员中。
3. 到港窗口：`eta` 非空、未到港（无 ATA），且 `0 <= ETA日期 - 今天 <= warning_days`。
4. 防重复：`event_key = group_id + SINGLE_IN_TRANSIT_ETA + shipment_id + eta_date`。
5. 严重级别：`info`；提醒卡片使用船舶图标与青绿色主题。

提醒示例：

```text
单票在途货物即将到港
客户 ABC 当前仅有一票在途（SN-001），预计 2026-06-25 到港，还有 5 天。
```

## 分组方式

### 1. 手动分组

在运单列表勾选多票运单，点击：

- 新建分组
- 加入已有分组
- 移出分组
- 配置组规则

这是首版优先实现方式，最贴合实际操作。

### 2. 自动建议成组

后续可以根据以下字段生成成组建议：

- `customer + customer_no`
- `customer + vessel_voyage`
- `customer + destination_port_code + eta`
- `amazon_ref_id`
- `customer_shipment_id`

建议先做“推荐成组”，由用户确认后落库，不建议首版自动强制成组。推荐逻辑只负责建议哪些货物可以组成一组，不负责决定要启用哪些规则。

### 3. Excel 导入分组

后续可在运单导入模板中增加：

- 分组编号
- 分组名称
- 启用规则
- 规则配置

导入时按 `group_no` 自动创建或更新分组关系，并按导入内容写入 `shipment_group_rules`。

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

执行流程：

1. 查询需要评估的分组。
2. 查询每个分组启用的 `shipment_group_rules`。
3. 按 `rule_type` 分发到对应规则处理器。
4. 规则处理器读取组成员和运单状态。
5. 生成或跳过 `shipment_group_notifications`。

调用入口：

1. 计划任务定时扫描，例如每 1 小时扫描一次。（**未实现**）
2. **运单轨迹同步后**，对本次有更新的运单所在分组即时评估（`evaluate_groups_after_tracking_sync`，内部/承运商同步均已接入）。
3. 用户在分组详情页点击“重新计算提醒”。

## API 设计

建议新增接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/shipment-groups` | 分组列表，支持按客户、船名航次、目的港、收款状态、规则类型筛选 |
| `POST` | `/api/v1/shipment-groups` | 新建分组 |
| `GET` | `/api/v1/shipment-groups/{id}` | 分组详情 |
| `PUT` | `/api/v1/shipment-groups/{id}` | 更新分组 |
| `DELETE` | `/api/v1/shipment-groups/{id}` | 删除分组 |
| `POST` | `/api/v1/shipment-groups/{id}/members` | 添加成员 |
| `DELETE` | `/api/v1/shipment-groups/{id}/members` | 移除成员 |
| `GET` | `/api/v1/shipment-groups/{id}/rules` | 分组规则列表 |
| `PUT` | `/api/v1/shipment-groups/{id}/rules` | 覆盖更新分组启用规则 |
| `PATCH` | `/api/v1/shipment-groups/{id}/rules/{ruleType}` | 更新单条规则配置或开关 |
| `GET` | `/api/v1/shipment-groups/{id}/notifications` | 分组提醒列表 |
| `POST` | `/api/v1/shipment-groups/{id}/evaluate-alerts` | 手动重新计算提醒 |
| `POST` | `/api/v1/shipment-group-notifications/read-all` | 分组提醒全部已读 |

运单列表接口可扩展筛选参数：

```text
groupId
groupNo
hasGroup
ruleType
hasRule
```

分组创建/更新 payload 建议使用：

```json
{
  "groupName": "客户A 6月第一批",
  "customer": "客户A",
  "paymentStatus": "UNPAID",
  "rules": [
    {
      "ruleType": "BATCH_DELIVERY_DEADLINE",
      "enabled": true,
      "thresholdDays": 30,
      "warningDays": 7
    },
    {
      "ruleType": "GROUP_ARRIVED_PAYMENT",
      "enabled": true
    },
    {
      "ruleType": "SINGLE_IN_TRANSIT_ETA_WARNING",
      "enabled": true,
      "warningDays": 10
    }
  ]
}
```

后端需要保证：

- `rules` 可以为空；为空表示该组当前不自动产生规则提醒。
- 同一分组内 `ruleType` 不能重复。
- 只允许写入系统支持的 `ruleType`。
- 每类规则校验自己的必填配置，例如 `BATCH_DELIVERY_DEADLINE` 需要有效的 `thresholdDays` 和 `warningDays`；`SINGLE_IN_TRANSIT_ETA_WARNING` 需要有效的 `warningDays`（到港前提醒天数，默认 10）。
- 如果后续需要兼容旧字段 `groupType`，只能作为备注或迁移辅助，不参与规则启用判断。

## 前端设计

### 运单列表

在现有运单列表中增加：

- “分组”列，显示组名或组号。
- 分组筛选项，支持按分组、是否已分组、已启用规则筛选。
- 批量操作：
  - 新建分组
  - 加入已有分组
  - 移出分组
  - 配置组规则

### 分组管理页

新增页面 `/shipment-groups`。

页面结构：

- 左侧：分组列表和筛选，包含客户、船名航次、目的港、收款状态、启用规则。
- 右侧：分组详情。
- 详情展示：
  - 组内运单数
  - 已到港数
  - 已签收数
  - 未签收超时数
  - 收款状态
  - 已启用规则
  - 未读提醒
  - 组内运单明细

规则配置交互：

- 分组详情页提供“规则配置”区域。
- 支持启用/停用规则。
- 支持编辑规则阈值，例如签收期限天数和提前提醒天数。
- 保存规则后可提示用户是否立即重新计算提醒。

### 首页与顶栏提醒

复用现有通知风格，增加“分组提醒”来源：

- 顶栏铃铛显示未读组提醒。
- 首页海运预警区域可增加“分组提醒”面板。
- 点击提醒跳转到对应分组详情。

## 与现有模块的关系

| 现有模块 | 复用方式 |
| --- | --- |
| `shipments` | 分组成员来源，复用 `delivered_time`、`status_code`、`eta`、`ata` 等字段 |
| 轨迹同步 | 同步后触发组规则重新计算 |
| 运单订阅通知 | 可复用通知展示和已读交互思路 |
| 海运预警 | 复用到港状态判断逻辑 |
| 计划任务 | 增加组提醒扫描任务 |

## 审查结论：规则不应由分组类型推导

如果通过 `group_type` 或 `primary_type` 决定规则是否启用，会产生设计问题：

1. 一组货可能同时需要执行多种业务规则，类型容易变成互斥标签。
2. “为什么成组”和“执行什么规则”被耦合，后续新增规则时需要不断调整类型体系。
3. 前端筛选和后端规则判断容易出现歧义，例如到底筛选“某种类型的组”，还是“启用了某条规则的组”。
4. 用户真正关心的是这组货要不要执行某条规则，而不是这组货叫什么类型。

因此实现必须调整为：

```text
shipment_groups: 只保存组本身
shipment_group_members: 保存组内运单
shipment_group_rules: 保存该组启用的规则
shipment_group_notifications: 保存规则产生的提醒
```

所有规则判断、筛选、自动建议和 Excel 导入都应围绕 `shipment_group_rules` 展开。

## 实施路线

### 阶段一：基础分组

1. 新增分组相关表。
2. 新增分组 CRUD API。
3. 支持运单批量加入/移出分组。
4. 运单列表展示分组信息并支持分组筛选。

### 阶段二：规则配置

1. 新增 `shipment_group_rules` 表和规则配置 API。
2. 分组创建/编辑时支持配置启用规则。
3. 分组详情页展示和编辑规则配置。

### 阶段三：固定规则提醒

1. 实现 `BATCH_DELIVERY_DEADLINE`。
2. 实现 `GROUP_ARRIVED_PAYMENT`。
3. 新增分组提醒表和未读提醒接口。
4. 分组详情页展示提醒。

### 阶段四：通知中心接入

1. 顶栏铃铛聚合分组提醒。
2. 首页增加分组提醒区域。
3. 支持提醒已读和处理完成。

### 阶段五：自动成组建议

1. 根据客户、客户单号、船名航次、目的港等字段生成候选分组。
2. 用户确认后批量创建分组。
3. Excel 导入支持分组字段和规则字段。

## 设计取舍

首版不建议做过度通用的低代码规则引擎。当前业务规则明确，使用 `rule_type + threshold_days + warning_days + config_json` 已经足够。这样既能快速落地，也能为后续扩展“预约送仓超时、清关超时、查验未解除”等规则保留空间。
