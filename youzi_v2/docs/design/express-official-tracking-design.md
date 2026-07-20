# 快递官网轨迹自动查询设计方案

## 背景

一票运单的实际运输可能有两种尾端履约方式：

```text
承运商负责运输
  ├─ 承运商直接卡派到门：承运商轨迹覆盖完整运输过程
  └─ 承运商转交快递：承运商轨迹 + UPS/FedEx 等快递官网轨迹
```

现有系统已经具备：

- 运单主转单号 `shipments.tracking_number`
- 快递公司编码 `shipments.express_code`
- 多跟踪号表 `shipment_tracking_numbers`
- 内部轨迹、承运商轨迹和后台定时任务
- UPS、FedEx、DHL、DPD、CWE 等号码规范化和初步识别规则

本方案在现有承运商轨迹之外，增加独立的“快递官网轨迹”。第一阶段接入 UPS、FedEx 官网 API，每天自动查询已经成功写入主转单号的运单。

## 第一阶段目标

```text
发现有效主转单号
  → 识别 UPS/FedEx
  → 创建快递官网查询记录
  → 每天自动查询一次
  → 保存当前状态、预计送达和完整轨迹节点
  → 在运单列表和轨迹抽屉中展示
```

第一阶段范围：

- 仅查询主转单号。
- 首批支持 UPS、FedEx。
- 自动任务默认每天执行一次，并提供单票手动立即更新。
- 主单签收只更新快递轨迹状态。
- 不回写 `shipments.delivered_time`。
- 不自动将整票运单改为已签收。
- 不根据“承运商已交快递”节点生成等待转单号提醒。
- 暂不生成“轨迹长期未更新”异常，但保留判断所需的数据。

后续范围：

- DHL、DPD 等更多快递官网适配器。
- 从承运商接口或快递官网响应中解析每件子单号。
- 按子单号汇总部分签收、全部签收。
- 节点长期未更新、预计送达逾期等异常规则。
- 区分哪些渠道或运输方式必须转交快递，并生成“等待转单号”提醒。

## 轨迹边界

三类轨迹分别保存，不互相覆盖：

| 类型 | 数据来源 | 说明 |
| --- | --- | --- |
| 内部轨迹 | DPS/WMS | 内部运输和业务节点 |
| 承运商轨迹 | 渠道商、物流供应商 API | 头程、海运、清关、海外仓、卡派或交快递 |
| 快递官网轨迹 | UPS、FedEx 等官网 API | 尾程包裹揽收、运输、派送、签收和异常 |

现有 `carrier_tracking_logs` 继续只保存承运商轨迹。快递官网轨迹使用独立数据表，避免同一票的承运商轨迹和尾程轨迹互相替换摘要。

## 查询触发条件

满足以下条件时进入自动查询范围：

1. `shipments.tracking_number` 已成功写入且非空。
2. `express_code` 能明确识别快递公司，或可通过号码规则识别。
3. 快递公司已经启用并配置官网 API。
4. 运单未取消，且整票尚未在业务系统中完成签收。
5. 当前快递查询记录未被人工停用。

识别优先级：

```text
shipments.express_code
  > 带快递公司名称的号码前缀
  > 单号格式自动识别
```

`express_code` 优先于号码猜测。无法可靠识别时不请求官网 API，在页面显示“快递公司待确认”。

付款状态不影响快递轨迹查询。

## 主单号处理

第一阶段把 `shipments.tracking_number` 作为主单号查询，只创建一条 `is_main = 1` 的快递包裹记录。

当运单箱数大于 1 时，主单轨迹只代表当前可获得的主单查询结果：

- 页面明确显示“主单轨迹”。
- 主单签收不等于全部箱件已经确认签收。
- 不自动更新整票签收状态和 `delivered_time`。

建议同时展示：

```text
预计件数：shipments.ctns
已取得快递号码数：当前有效快递包裹记录数量
```

例如：`当前仅追踪主单，1/10 个号码`。

后续取得子单号时，追加 `is_main = 0` 的记录，不修改主单记录。届时可按全部有效子单号汇总“已签收 8/10”“全部签收”等状态。

## 快递状态

系统使用统一状态，适配器负责把 UPS/FedEx 原始状态映射为统一状态，同时保留原始代码和原始文案。

| 状态值 | 页面文案 | 说明 |
| --- | --- | --- |
| `PENDING` | 等待查询 | 已取得号码，尚未成功查询 |
| `NOT_FOUND` | 等待官网收录 | 官网查询成功，但暂时没有该号码 |
| `PICKED_UP` | 已揽收 | 快递公司已接收货物 |
| `IN_TRANSIT` | 运输中 | 快递网络运输中 |
| `OUT_FOR_DELIVERY` | 派送中 | 正在末端派送 |
| `DELIVERED` | 主单已签收 | 第一阶段不代表整票自动签收 |
| `EXCEPTION` | 快递异常 | 官网明确返回异常、中断或退回等状态 |
| `UNKNOWN` | 状态待识别 | API 返回了尚未映射的状态 |

“接口查询失败”和“官网暂未收录”必须分开：

- 查询失败：网络超时、鉴权失败、限流、官网服务异常。
- 暂未收录：API 调用成功，但官网还没有该号码的轨迹。

## 数据表设计

### 快递包裹状态表 `express_tracking_packages`

一条记录表示一个运单下的一个快递号码。第一阶段每票通常只有主单一条记录。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | TEXT PK | UUID |
| `shipment_id` | TEXT | 关联运单 ID |
| `shipment_no` | TEXT | 运单号，便于批量查询 |
| `tracking_number` | TEXT | 规范化后的快递号码 |
| `express_code` | TEXT | `UPS`、`FEDEX` 等 |
| `is_main` | INTEGER | `1` 主单，`0` 子单 |
| `parent_tracking_number` | TEXT NULL | 后续子单关联主单 |
| `number_source` | TEXT | `CARRIER_API`、`DPS`、`MANUAL` 等 |
| `status_code` | TEXT | 系统统一状态 |
| `raw_status_code` | TEXT | 官网原始状态代码 |
| `raw_status_desc` | TEXT | 官网原始状态文案 |
| `estimated_delivery_time` | TEXT NULL | 快递官网预计送达时间 |
| `latest_event_time` | TEXT NULL | 官网最新轨迹节点时间 |
| `latest_event_desc` | TEXT | 官网最新轨迹描述 |
| `last_changed_time` | TEXT NULL | 本地最后发现状态或节点变化的时间 |
| `last_sync_time` | TEXT NULL | 最后一次查询尝试时间 |
| `last_success_time` | TEXT NULL | 最后一次成功请求官网的时间 |
| `next_sync_time` | TEXT NULL | 下次计划查询时间 |
| `consecutive_failures` | INTEGER | 连续接口失败次数 |
| `last_error_code` | TEXT NULL | 最后错误代码 |
| `last_error_message` | TEXT NULL | 最后错误摘要，不保存密钥或令牌 |
| `exception_status` | TEXT NULL | 后续异常规则预留 |
| `is_active` | INTEGER | 是否继续自动查询 |
| `created_time` | TEXT | 创建时间 |
| `updated_time` | TEXT | 更新时间 |

建议约束和索引：

```text
UNIQUE(shipment_id, tracking_number)
INDEX(express_code, is_active, next_sync_time)
INDEX(shipment_no)
INDEX(status_code, latest_event_time)
```

不直接保存 `unchanged_days` 作为唯一事实。需要时根据 `last_changed_time` 动态计算，避免定时任务停机期间被误判为“官网轨迹长期未更新”。

### 快递轨迹节点表 `express_tracking_logs`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | TEXT PK | UUID |
| `package_id` | TEXT | 关联快递包裹记录 |
| `shipment_no` | TEXT | 运单号 |
| `tracking_number` | TEXT | 快递号码 |
| `express_code` | TEXT | UPS、FedEx 等 |
| `event_time` | TEXT | 节点发生时间 |
| `event_code` | TEXT NULL | 官网节点代码 |
| `event_desc` | TEXT | 标准展示文案 |
| `raw_event_desc` | TEXT | 官网原始文案 |
| `location` | TEXT NULL | 节点地点 |
| `vendor_event_id` | TEXT NULL | 官网事件 ID，用于稳定去重 |
| `created_time` | TEXT | 首次写入时间 |

优先使用官网事件 ID 去重；官网没有事件 ID 时，使用以下组合去重：

```text
tracking_number + event_time + event_code + raw_event_desc + location
```

### 同步任务记录

复用现有 `tracking_sync_jobs`，新增 `source = express`，记录：

- 查询号码数
- 有变化号码数
- 新增轨迹节点数
- 暂未收录数
- 查询失败数
- 按 UPS/FedEx 汇总的执行结果

## 号码变化

运单主转单号发生变化时：

1. 原号码记录保留轨迹历史。
2. 原号码设置 `is_active = 0`，停止自动查询。
3. 新号码创建新的主单记录并开始查询。
4. 不覆盖或删除旧号码的轨迹节点。

如果只是重复写入同一个号码，不重复创建任务。

## 官网 API 适配层

增加统一适配器接口，例如：

```python
class ExpressTrackingProvider:
    def authenticate(self) -> None: ...
    def track(self, tracking_number: str) -> ExpressTrackingResult: ...
```

统一返回结构至少包含：

```text
tracking_number
status_code
raw_status_code
raw_status_desc
estimated_delivery_time
events[]
not_found
```

首批实现：

- `UpsTrackingProvider`
- `FedexTrackingProvider`

每个适配器独立负责：

- OAuth 令牌获取和进程内缓存
- 请求参数和响应解析
- 官网状态到系统统一状态的映射
- 时间、时区和地点规范化
- 限流、超时和可重试错误识别

不抓取 UPS/FedEx 官网 HTML 页面，不依赖浏览器自动化或验证码绕过。

## 私密配置

UPS、FedEx 开发者 API 凭证继续放在仓库根目录：

```text
config/config.json
```

该文件已经被 `.gitignore` 忽略，不提交 Git。建议新增以下配置结构：

```json
{
  "express_tracking": {
    "providers": {
      "UPS": {
        "enabled": true,
        "environment": "production",
        "base_url": "https://onlinetools.ups.com",
        "client_id": "本地填写",
        "client_secret": "本地填写"
      },
      "FEDEX": {
        "enabled": true,
        "environment": "production",
        "base_url": "https://apis.fedex.com",
        "client_id": "本地填写",
        "client_secret": "本地填写"
      }
    }
  }
}
```

要求：

- 日志、数据库和 API 响应不得记录 `client_secret` 或完整 OAuth token。
- OAuth token 只在进程内短期缓存，到期后重新获取。
- 测试环境和生产环境通过 `environment`、`base_url` 区分。
- 凭证缺失时只禁用对应官网适配器，不影响内部轨迹和承运商轨迹任务。

自动任务启用状态和执行时间建议继续使用现有 `app_settings`，由“计划任务”页面管理；凭证和官网地址保留在私密配置文件中。

建议默认配置：

```text
任务名称：快递官网轨迹
启用状态：凭证配置完成后开启
执行时间：北京时间每天 02:00
```

## 定时同步

复用现有后台调度线程，每分钟检查是否存在到期任务，但只有满足 `next_sync_time <= now` 的记录才会请求官网。

第一阶段调度规则：

- 新号码创建后允许立即查询一次。
- 正常未签收号码每天查询一次。
- `NOT_FOUND` 每天重试一次。
- 接口失败记录失败次数，下一天继续重试。
- 官网主单显示签收后停止定时查询。
- 提供单票“立即更新官网轨迹”，不受每日时间限制，但需要防止短时间重复点击。

同步应按快递公司分组，并设置小批次、请求间隔和超时，避免一次失败影响整批任务。

## 预计送达时间

快递官网预计送达时间保存在：

```text
express_tracking_packages.estimated_delivery_time
```

第一阶段不覆盖现有 `shipments.expected_delivery_time`。页面明确区分：

- 承运商预计送达
- UPS/FedEx 官网预计送达

运单列表可优先展示快递官网预计送达，但必须保留来源标识。

## 页面设计

### 运单列表

在“轨迹”列前展示综合状态。进入快递段后可显示：

```text
等待 UPS 收录
UPS 已揽收
UPS 运输中
UPS 派送中
UPS 主单已签收
UPS 异常
```

可增加筛选：

- 有快递主单
- 快递公司
- 快递状态
- 官网预计送达日期
- 官网轨迹最后更新时间
- 官网查询失败

### 轨迹抽屉

轨迹抽屉调整为三个页签：

```text
内部轨迹 / 承运商轨迹 / 快递轨迹
```

快递轨迹页签展示：

- 快递公司和主单号
- “主单轨迹”标识
- 当前统一状态和官网原始状态
- 官网预计送达时间
- 最新查询时间
- 轨迹时间线
- 手动“立即更新官网轨迹”操作
- 查询失败或等待官网收录提示

## API 建议

```text
GET  /api/v1/shipments/{id}/express-tracking
POST /api/v1/shipments/{id}/sync-express-tracking
GET  /api/v1/express-tracking/packages
GET  /api/v1/express-tracking/jobs
GET  /api/v1/scheduled-tasks/express-tracking-settings
PUT  /api/v1/scheduled-tasks/express-tracking-settings
POST /api/v1/scheduled-tasks/express-tracking/run-now
```

手动同步接口返回本次查询是否成功、是否发现变化、新增节点数和错误摘要，不返回官网密钥或 OAuth token。

## 通知和异常预留

第一阶段：

- 普通快递轨迹变化不进入顶部待办。
- `NOT_FOUND` 不视为运输异常。
- 查询失败不进入顶部待办，只在计划任务和轨迹页显示。
- 官网返回 `EXCEPTION` 时先在运单列表和轨迹抽屉突出显示。

后续异常规则可以基于以下数据实现：

- `latest_event_time`
- `last_changed_time`
- `last_sync_time`
- `last_success_time`
- `consecutive_failures`
- `estimated_delivery_time`
- `status_code`

后续候选规则：

- 等待官网收录超过 N 天。
- 已揽收后超过 N 天无新节点。
- 运输中超过 N 天无新节点。
- 派送中超过 N 小时仍未签收。
- 官网预计送达已过期仍未签收。
- 官网接口连续失败超过 N 次。

异常生成后可以接入现有运单异常和跟进体系。顶部待办只聚合真正需要人工处理的异常，不推送每一次普通轨迹更新。

未来增加“等待转单号”提醒时，需要先具备可靠的“该票必须交快递”判断依据，例如：

- 渠道或派送方式配置 `last_mile_required`。
- 承运商标准节点明确标识已交快递。
- 承运商接口返回尾程类型和快递公司。

在具备可靠判断前，不根据轨迹文案猜测，也不生成该类提醒。

## 第一阶段验收口径

1. 有 UPS/FedEx 主转单号的有效运单能自动创建查询记录。
2. 每天自动查询到期主单，单票也可手动立即查询。
3. 官网状态、预计送达和轨迹节点能够稳定保存并去重。
4. 内部轨迹、承运商轨迹和快递官网轨迹互不覆盖。
5. 官网暂未收录与接口查询失败能够正确区分。
6. 主单签收不会修改 `shipments.delivered_time` 或整票签收状态。
7. 转单号变更后保留旧轨迹，新号码开始独立查询。
8. 凭证和 OAuth token 不出现在日志、数据库或前端响应中。
9. 缺少某家快递凭证时，不影响系统其他轨迹同步任务。
10. 数据结构可以在不迁移主表逻辑的情况下追加子单号和异常规则。
