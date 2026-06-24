# 内部轨迹时间字段回写设计方案

## 背景

当前系统会同步或维护运单内部轨迹，运营人员也会手动更新轨迹内容。业务希望根据内部轨迹自动回写运单上的关键时间字段：

- `ETD`：预计离港时间
- `ATD`：实际离港时间
- `ETA`：预计到港时间
- `ATA`：实际到港时间
- `expected_delivery_time`：预计送仓时间
- `signed_time`：签收时间

内部轨迹的英文描述相对稳定，但存在空格、标点、大小写、中文补充说明等轻微变化。同时部分轨迹由人工补录，轨迹事件时间可能和真实业务发生时间存在偏差。例如预计 `6/15` 送仓，但运营到 `6/28` 才补录签收轨迹。

因此本方案不建议简单按轨迹文本直接覆盖正式字段，而是采用“轨迹识别、候选值生成、自动回写、冲突审批”的方式处理。

## 设计目标

1. 支持从内部轨迹中识别 `ETD`、`ATD`、`ETA`、到港、预计送仓、签收等节点。
2. `ETD`、`ATD`、`ETA` 以最新包含对应字段的轨迹为准，允许后续轨迹更新覆盖。
3. `ATA` 不解析文本日期，匹配到 `Arriving at the destination` 节点后使用该轨迹的事件时间。
4. `expected_delivery_time` 从 `Expected to be delivered on` 轨迹中解析，一般自动回写。
5. `signed_time` 从 `signed for` 或首字母大写 `Delivered` 节点识别，但当签收节点事件日期和预计送仓日期不一致时进入人工审批。
6. 所有自动识别结果保留来源轨迹和审批状态，方便追溯、纠错和后续优化。

## 核心原则

### 状态识别和时间回写分离

轨迹可以自动识别业务状态，例如“已到港”“已签收”。但时间字段是否直接回写，需要根据字段类型和置信度判断。

```text
轨迹识别结果 = 系统根据文本和事件时间解析出的候选结果
正式时间字段 = 经过自动规则或人工审批后确认写入运单的业务字段
```

签收轨迹即使因为时间冲突进入人工审批，仍然可以把运单状态识别为已签收；只是正式 `signed_time` 暂不自动覆盖。

### 显式日期优先

`ETD`、`ATD`、`ETA` 只从轨迹文本中的显式字段解析，不从清关、到港、签收等节点反推。

示例：

```text
LURLINE/100E ETD:5/27 ETA:6/9
LURLINE/100E ATD:5/27 ETA:6/9
```

其中 `ETD:5/27`、`ATD:5/27`、`ETA:6/9` 是高置信度字段，可以自动回写。

### 以轨迹事件时间为准

`ATA` 和 `signed_time` 的文本通常不带明确日期，因此使用轨迹的事件时间，而不是操作更新时间。

推荐区分：

```text
track_event_time = 轨迹代表的业务事件时间
created_time / updated_time = 系统记录或人工维护时间
```

如果当前系统没有独立的 `track_event_time`，则需要明确字段语义：系统回写的是“内部轨迹记录时间”，不是严格意义上的真实业务发生时间。

### 候选值自动生成，冲突才审批

候选字段不需要全部人工判断。只要轨迹被识别，就可以自动生成候选结果。正式字段大部分自动回写，只有存在业务冲突或低置信度时进入人工审批。

首版人工审批重点只放在签收时间冲突：

```text
签收节点事件日期 != 最新预计送仓日期
```

## 轨迹识别规则

### 文本预处理

识别前先做轻量归一化：

1. 全角冒号 `：` 转半角冒号 `:`
2. 多个空白字符压缩为一个空格
3. 去除首尾空格
4. `ETD`、`ETA`、`ATD` 字段大小写可统一处理
5. 主体英文节点可做 lowercase 匹配
6. `Delivered` 节点保持大小写敏感，只识别首字母大写的 `Delivered`

### ETD / ATD / ETA

匹配规则：

```regex
\b(ETD|ETA|ATD)\s*:?\s*(\d{1,2})[\/.-](\d{1,2})\b
```

可匹配示例：

```text
ETD:5/27
ETD : 5/27
ETA：6/9
ATD 5/27
```

回写规则：

| 字段 | 候选来源 | 正式字段回写 |
| --- | --- | --- |
| `ETD` | 最新一条包含 `ETD` 的轨迹 | 自动回写，可覆盖旧值 |
| `ETA` | 最新一条包含 `ETA` 的轨迹 | 自动回写，可覆盖旧值 |
| `ATD` | 最新一条包含 `ATD` 的轨迹 | 自动回写，可覆盖旧值 |

“最新”按轨迹事件时间排序；如果事件时间相同，再按轨迹创建时间或轨迹 ID 做稳定排序。

### ATA

匹配英文主体：

```regex
arriving\s+at\s+the\s+destination
```

标准示例：

```text
Arriving at the destination, waiting for unloading
```

回写规则：

```text
candidate_ata = 最新匹配到港节点的 track_event_time
ata = candidate_ata
```

说明：

- 当前不单独解析文本里的 ATA 字段。
- 不使用“进口清关放行”节点反推 ATA。
- 若轨迹没有可靠事件时间，可生成候选值但标记低置信度，是否自动写正式字段由后续实现策略决定。

### 预计送仓时间

匹配英文主体：

```regex
expected\s+to\s+be\s+delivered\s+on\s+(\d{1,2})[\/.-](\d{1,2})
```

标准示例：

```text
Expected to be delivered on 6/14
```

回写规则：

```text
candidate_expected_delivery_time = 最新 Expected to be delivered on 轨迹解析出的日期
expected_delivery_time = candidate_expected_delivery_time
```

预计送仓时间一般较可信，首版自动回写，不进入人工审批。

### 签收时间

签收节点有两类：

```regex
signed\s+for
```

以及大小写敏感：

```regex
\bDelivered\b.*
```

标准示例：

```text
Your goods have been signed for
Delivered xxx
```

说明：

- `signed for` 可 lowercase 匹配。
- `Delivered` 只识别首字母大写，避免误伤普通描述中的 `delivered`。
- 签收时间候选值使用签收节点轨迹事件时间，不从文本中解析日期。

## 候选字段和正式字段

推荐在运单主表或扩展表中保留正式字段：

```text
etd
eta
atd
ata
expected_delivery_time
signed_time
```

同时保留解析候选和审计信息。字段可以按实际数据库设计拆成独立表，推荐结构如下：

```sql
CREATE TABLE shipment_tracking_time_candidates (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    candidate_value TEXT NOT NULL,
    source_track_id TEXT NOT NULL,
    source_track_time TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'high',
    review_status TEXT NOT NULL DEFAULT 'auto_confirmed',
    review_reason TEXT NOT NULL DEFAULT '',
    applied INTEGER NOT NULL DEFAULT 0,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    UNIQUE(shipment_id, field_name)
);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `field_name` | 候选字段名，例如 `etd`、`signed_time` |
| `candidate_value` | 系统识别出的候选时间 |
| `source_track_id` | 来源内部轨迹 ID |
| `source_track_time` | 来源轨迹事件时间 |
| `confidence` | `high`、`medium`、`low` |
| `review_status` | `auto_confirmed`、`pending_review`、`manual_approved`、`manual_rejected` |
| `review_reason` | 进入审批或被拒绝的原因 |
| `applied` | 是否已写入正式字段 |

如果不希望新增候选表，也可以把审计字段直接放在运单表或运单扩展表中：

```text
etd_source_track_id
eta_source_track_id
atd_source_track_id
ata_source_track_id
expected_delivery_source_track_id
signed_time_candidate
signed_time_source_track_id
signed_time_review_status
signed_time_review_reason
```

首版更推荐独立候选表，便于后续扩展审批历史和回写审计。

## 自动回写规则

### 字段级策略

| 字段 | 候选生成 | 正式字段自动回写 | 人工审批 |
| --- | --- | --- | --- |
| `ETD` | 最新显式 `ETD` | 是 | 否 |
| `ETA` | 最新显式 `ETA` | 是 | 否 |
| `ATD` | 最新显式 `ATD` | 是 | 否 |
| `ATA` | 最新到港节点事件时间 | 是 | 异常时可扩展 |
| `expected_delivery_time` | 最新预计送仓节点解析日期 | 是 | 否 |
| `signed_time` | 最新签收节点事件时间 | 条件自动 | 冲突时需要 |

### 签收时间审批规则

签收状态和签收时间分开处理：

```text
识别到 signed for 或 Delivered:
  运单状态可标记为已签收
  signed_time_candidate = 签收节点 track_event_time
```

正式 `signed_time` 回写规则：

```text
如果存在 signed_time_candidate:
  如果不存在 expected_delivery_time:
    signed_time = signed_time_candidate
    review_status = auto_confirmed

  如果存在 expected_delivery_time:
    如果 same_date(signed_time_candidate, expected_delivery_time):
      signed_time = signed_time_candidate
      review_status = auto_confirmed
    否则:
      signed_time 不覆盖
      review_status = pending_review
      review_reason = 签收节点事件日期与预计送仓日期不一致
```

日期比较只比较日期，不比较时分秒：

```text
2026-06-15 09:30
2026-06-15 18:00
```

以上两者视为同一天。

首版采用严格同日判断。如果后续业务允许仓库次日凌晨签收，可以扩展为允许 `0-1` 天容差。

## 年份补全规则

内部轨迹常见日期格式为 `5/27`、`6/9`，没有年份。解析时需要补全年份。

推荐策略：

1. 优先使用轨迹事件时间的年份。
2. 如果解析出的日期与轨迹事件时间相差超过 180 天，允许跨年修正。
3. 如果没有轨迹事件时间，则使用运单创建时间或船期相关时间的年份。
4. 不建议直接使用系统当前年份，避免历史数据重算时产生错误。

示例：

```text
轨迹事件时间：2026-05-20
文本：ETD:5/27 ETA:6/9
解析结果：2026-05-27、2026-06-09
```

跨年示例：

```text
轨迹事件时间：2026-12-28
文本：ETA:1/5
解析结果：2027-01-05
```

## 处理流程

```text
同步或新增内部轨迹
  -> 读取该运单全部内部轨迹
  -> 文本归一化
  -> 逐条识别 ETD / ETA / ATD / ATA / 预计送仓 / 签收节点
  -> 按字段选择最新候选值
  -> 写入候选表或候选审计字段
  -> 按自动回写规则更新正式字段
  -> 签收时间冲突时生成 pending_review
```

伪代码：

```python
def recalculate_tracking_time_fields(shipment_id):
    tracks = load_internal_tracks(shipment_id)
    parsed_events = [parse_track(track) for track in tracks]

    candidates = {
        "etd": latest_explicit_date(parsed_events, "ETD"),
        "eta": latest_explicit_date(parsed_events, "ETA"),
        "atd": latest_explicit_date(parsed_events, "ATD"),
        "ata": latest_track_time(parsed_events, "ARRIVED_DESTINATION"),
        "expected_delivery_time": latest_expected_delivery_date(parsed_events),
        "signed_time": latest_track_time(parsed_events, "SIGNED"),
    }

    save_candidates(shipment_id, candidates)

    auto_apply(shipment_id, "etd", candidates["etd"])
    auto_apply(shipment_id, "eta", candidates["eta"])
    auto_apply(shipment_id, "atd", candidates["atd"])
    auto_apply(shipment_id, "ata", candidates["ata"])
    auto_apply(shipment_id, "expected_delivery_time", candidates["expected_delivery_time"])

    apply_signed_time_with_review(
        shipment_id,
        signed_time=candidates["signed_time"],
        expected_delivery_time=candidates["expected_delivery_time"],
    )
```

## 人工审批

首版只需要支持签收时间冲突审批。

### 进入审批的条件

```text
存在签收节点
且存在预计送仓时间
且签收节点事件日期 != 预计送仓日期
```

### 审批界面建议展示

- 运单号
- 当前正式签收时间
- 候选签收时间
- 预计送仓时间
- 来源签收轨迹文本
- 来源签收轨迹事件时间
- 来源预计送仓轨迹文本
- 来源预计送仓日期
- 冲突原因

### 审批动作

| 动作 | 结果 |
| --- | --- |
| 通过候选签收时间 | 写入正式 `signed_time`，`review_status = manual_approved` |
| 拒绝候选签收时间 | 不覆盖正式字段，`review_status = manual_rejected` |
| 手动填写签收时间 | 写入人工指定时间，记录审批人和审批备注 |

后续可以增加审批历史表：

```sql
CREATE TABLE shipment_tracking_time_reviews (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    action TEXT NOT NULL,
    old_value TEXT NOT NULL DEFAULT '',
    new_value TEXT NOT NULL DEFAULT '',
    reviewer TEXT NOT NULL,
    review_note TEXT NOT NULL DEFAULT '',
    reviewed_time TEXT NOT NULL
);
```

## 示例

### 示例一：船期更新

轨迹：

```text
2026-05-20 LURLINE/100E ETD:5/27 ETA:6/9
2026-05-25 LURLINE/100E ETD:5/28 ETA:6/10
2026-05-28 LURLINE/100E ATD:5/28 ETA:6/10
```

结果：

```text
ETD = 2026-05-28
ATD = 2026-05-28
ETA = 2026-06-10
```

### 示例二：到港

轨迹：

```text
2026-06-09 Arriving at the destination, waiting for unloading
```

结果：

```text
ATA = 2026-06-09
ATA 来源 = 该到港轨迹
```

### 示例三：签收自动确认

轨迹：

```text
2026-06-10 Expected to be delivered on 6/14
2026-06-14 Your goods have been signed for
```

结果：

```text
expected_delivery_time = 2026-06-14
signed_time_candidate = 2026-06-14
signed_time = 2026-06-14
signed_time_review_status = auto_confirmed
```

### 示例四：签收进入人工审批

轨迹：

```text
2026-06-10 Expected to be delivered on 6/15
2026-06-28 Your goods have been signed for
```

结果：

```text
expected_delivery_time = 2026-06-15
signed_time_candidate = 2026-06-28
signed_time 不自动覆盖
signed_time_review_status = pending_review
signed_time_review_reason = 签收节点事件日期 2026-06-28 与预计送仓日期 2026-06-15 不一致
```

### 示例五：Delivered 节点

轨迹：

```text
2026-06-14 Delivered to Amazon FC
```

结果：

```text
识别为签收节点
signed_time_candidate = 2026-06-14
```

如果文本为：

```text
2026-06-14 goods delivered to Amazon FC
```

首版不按 `Delivered` 规则识别，因为 `delivered` 不是首字母大写。

## 边界和异常

### 多条签收轨迹

首版取最新签收节点事件时间作为候选值。

如果旧候选已经进入人工审批但尚未处理，后续出现新的签收轨迹时，可以更新候选值并保留旧审批记录。

### ETA 持续变化

`ETA` 会随船期变化持续更新，因此正式 `ETA` 始终取最新显式 `ETA`。不需要人工审批。

### ETD 持续变化

`ETD` 也可能更新，因此正式 `ETD` 取最新显式 `ETD`，不锁定第一条预配船期。

### 清关节点

以下节点只作为状态参考，不参与本方案的时间字段回写：

```text
Export customs clearance has been released
Customs clearance has been released.
```

后续如果需要清关时间字段，可以独立增加 `export_customs_released_time`、`import_customs_released_time`。

## 推荐落地顺序

1. 实现轨迹文本解析器，覆盖 `ETD`、`ETA`、`ATD`、到港、预计送仓、签收节点。
2. 实现按运单重算候选值的服务。
3. 自动回写 `ETD`、`ETA`、`ATD`、`ATA`、`expected_delivery_time`。
4. 实现签收时间同日判断，冲突时生成 `pending_review`。
5. 在运单详情或异常任务中展示签收时间审批入口。
6. 补充解析和回写单元测试，覆盖空格、冒号、大小写、跨年、签收冲突等场景。

