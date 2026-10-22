# DPS 更新亚马逊（dps_update_amz）

状态：**已实现。** 行为以本文为准。

在「补货件号 / 预约号」保存成功后，由本系统代发 DPS 接口，把起运港、目的港推给亚马逊侧。浏览器不直连 DPS。

## 触发

入口是运单列表的「补货件号 / 预约号」弹窗（`ShipmentAmazonRefModal`）。本地保存成功之后才推送。

同时满足才调用接口：

- 有 `waybillId`（DPS 运单主键）
- 本次保存的货件号非空（预约号可空，只填货件号即可推送）
- 能解析出起运港和目的港（见下文）

缺 `waybillId`、货件号为空或港口解析失败时，本地保存仍然保留，不调用 DPS，并提示缺什么。

`type` 固定为字符串 `"1"`，不提供其它事件类型。

## 配置

根目录 `config/config.json`（不进 Git）增加块 **`dps_update_amz`**：

| 键 | 说明 |
|----|------|
| `url` | 完整请求地址 |

鉴权使用根级 **`dps_authorization`**（与 `dps_route_status_query` 等相同）。真实 URL、Token 不写入业务代码和文档。

## 请求体

`Content-Type: application/json`。字段：

| 字段 | 来源 | 规则 |
|------|------|------|
| `orderId` | `shipments.waybill_id` | 必填 |
| `shipmentId` | 本次保存的货件号 `customer_shipment_id` | 必填 |
| `referenceId` | 本次保存的预约号 `amazon_ref_id` | 始终带上；为空时传 `""` |
| `originPort` | 港口规则解析 | 必填 |
| `destinationPort` | 用户选择或规则解析 | 必填 |
| `type` | 常量 | `"1"` |

示例（预约号为空）：

```json
{
  "orderId": "2104873261386080258",
  "shipmentId": "2555292WFB",
  "referenceId": "",
  "originPort": "CNNBO",
  "destinationPort": "USLAX",
  "type": "1"
}
```

港口码长度按运输方式：

| 运输方式 | 码 |
|----------|----|
| 空运 | 三字码，如 `SZX`、`LAX` |
| 海运 | 五字码，如 `CNSNZ`、`USLAX` |

## 运输方式

渠道类别 `channel_codes.category`：

- 等于 **`空运`** → 空运
- 其它（快船、普船、卡航、铁路等）→ 海运

类别缺失时视为海运，并在推送前提示无法确认空运规则。

## 限流

同一运单（按 `waybillId`）**一分钟内只允许推送一次**。成功和失败都占用冷却。

- 前端：一旦发出推送，按钮进入 60 秒冷却，并显示剩余秒数。
- 后端：按该票校验，60 秒内返回 429，避免绕过页面。冷却从本次推送请求发出时起算，不等待 DPS 返回成功。

## 港口规则表

新码表 **`amz_update_port_rules`**，后台名称「亚马逊推送港口」。走现有码表维护（增删改、启停），不写入 `config.json`。不复用 `port_codes`（该表现有字段无法表达运输方式、默认项和匹配方式）。

| 字段 | 说明 |
|------|------|
| `code` | 主键，如 `AIR_DEST_US_LAX` |
| `transport_mode` | `AIR` / `SEA` |
| `country_code` | 目的国二字码；起运规则可为 `CN` |
| `leg` | `ORIGIN` / `DESTINATION` |
| `port_code` | 推送用港口码（空运三字、海运五字） |
| `name_zh` | 展示名 |
| `rule_kind` | `DEFAULT` / `OPTION` / `ORIGIN_EXACT` / `DEST_KEYWORD` |
| `match_text` | 精确仓名，或目的港关键字；默认行留空 |
| `is_default` | 该组默认项（下拉默认、无关键字时的目的港） |
| `sort_order` | 下拉顺序 |
| `is_active` | 1 启用 |
| `created_time` / `updated_time` | `YYYY-MM-DD HH:mm:ss` |

`rule_kind`：

| 值 | 用途 |
|----|------|
| `DEFAULT` | 无其它命中时使用（空运起运、非美加空运目的、海运各国默认目的） |
| `OPTION` | 供弹窗下拉（仅美国、加拿大空运目的港） |
| `ORIGIN_EXACT` | `origin_warehouse_code` **整段相等**于 `match_text` |
| `DEST_KEYWORD` | 仅美国海运：在约定文本中包含 `match_text` 时覆盖默认目的港 |

### 运单上记住用户选择

`shipments` 保存窗口里确认过的 **`amz_push_origin_port`**、**`amz_push_dest_port`**。再次打开时回填；某侧为空时才用规则默认值。推送使用窗口里的港口，不再只在美国/加拿大空运时才允许改目的港。

## 空运种子

起运不看收货仓。

| leg | country | port_code | rule_kind | 说明 |
|-----|---------|-----------|-----------|------|
| ORIGIN | CN | SZX | DEFAULT | 固定起运 |
| DESTINATION | US | LAX | OPTION，默认 | 下拉默认 |
| DESTINATION | US | ORD | OPTION | |
| DESTINATION | US | JFK | OPTION | |
| DESTINATION | CA | YVR | OPTION，默认 | 下拉默认 |
| DESTINATION | CA | YYZ | OPTION | |
| DESTINATION | GB | LHR | DEFAULT | 无下拉 |
| DESTINATION | DE | FRA | DEFAULT | 无下拉 |
| DESTINATION | ES | FRA | DEFAULT | 无下拉 |
| DESTINATION | FR | FRA | DEFAULT | 无下拉 |
| DESTINATION | IT | FRA | DEFAULT | 无下拉 |
| DESTINATION | NL | FRA | DEFAULT | 无下拉 |

## 海运种子

起运按收货仓 **精确匹配** `origin_warehouse_code`。

| match_text | port_code |
|------------|-----------|
| 深圳仓 | CNSNZ |
| 义乌仓 | CNNBO |

不是这两档（空、别名、多空格）则起运港解析失败，不推送。

目的港：

| 国家 | 规则 | port_code |
|------|------|-----------|
| US | 默认 | USLAX |
| US | 关键字「萨瓦纳」 | USSAV |
| US | 关键字「纽约」 | USNYC |
| US | 关键字「奥克兰」 | USOAK |
| US | 关键字「西雅图」 | USSEA |
| US | 关键字「休斯顿」 | USHOU |
| CA | 默认，无关键字 | CAVAN |
| GB | 默认，无关键字 | GBFXT |
| DE、ES、FR、IT、NL | 默认，无关键字 | NLRTM |

美国海运关键字扫描字段（按序，命中即停）：`destination_port_code`、`delivery_address`、`address_code`、渠道中文名。不使用芝加哥 / `USCHI`。

欧洲范围就是德、西、法、意、荷这五个二字码，不扩大到其它欧洲国家。

## 解析顺序

1. 判定空运或海运。
2. 起运港：空运取 `AIR + ORIGIN + DEFAULT`（SZX）；海运取 `ORIGIN_EXACT`。
3. 目的港：
   - 空运且国家为 US 或 CA：用 `amz_push_dest_port`，否则用该国默认 `OPTION`。
   - 其它空运：该国 `DEFAULT`。
   - 海运且国家为 US：先 `DEST_KEYWORD`，否则 `USLAX`。
   - 其它海运：该国 `DEFAULT`（加 `CAVAN`、英 `GBFXT`、上述五国 `NLRTM`）。
4. 任一步无结果则不推送。

## 界面

弹窗在货件号、预约号之下始终显示 **起运港**、**目的港** 两个可编辑字段。打开时填入规则默认值；若该票曾经改过，则回填上次保存的值。保存和推送都使用窗口里的最终内容。美国空运默认仍是 LAX（可改为 ORD、JFK 或其它码），加拿大空运默认 YVR。

选项文案来自码表 `name_zh` 与 `port_code`。保存时与货件号、预约号一起写入；推送结果单独提示（成功 / DPS 错误信息）。推送失败不回滚已保存的货件号和预约号。

## 接口（实现时）

| 方法 | 路径 | 说明 |
|------|------|------|
| PATCH | 现有更新运单 | 增加 `amzPushDestPort`；货件号保存成功后服务端尝试推送 |
| GET | 码表 `amz_update_port_rules` | 复用码表列表，供下拉 |

推送本身不暴露 DPS URL。响应里给出是否已推送、跳过原因或 DPS 错误摘要。HTTP 状态低于 400 时仍解析 JSON：`code` 为 `200` 或 `0` 才算成功，否则把 `msg` 提示给用户。服务端记录该票最近一次推送时间（不论成败），用于 60 秒冷却；不记录 Token，也不保存对方响应原文。

## 不做

- 不在列表上单独做「推送到亚马逊」按钮（除非保存失败后的重试，仍走同一限流）。
- 不随 DPS 运单同步、ATD/ATA 自动推送。
- 不支持 `type` 除 `"1"` 以外的值。
- 不把港口规则写入 `config.json`。
