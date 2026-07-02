# 更新记录

按日期倒序记录 youzi_v2 的代码与文档变更。

## 2026-06-18

### 修复

- 运单分组规则评估：`BATCH_DELIVERY_DEADLINE` 使用未定义变量 `now` 导致整组评估失败，连带 `GROUP_ARRIVED_PAYMENT` 无法触发；各规则独立捕获异常，互不影响

- 轨迹同步（内部/承运商、含定时任务）完成后，对本次有更新的运单所在分组自动评估提醒；同步响应增加 `groupAlertsEvaluated` / `groupAlertsCreated`

- 分组详情「组内提醒」触发时间误显示为 JSON 对象；改为相对时间展示，悬停显示精确时间
- 分组预警卡片统一配色：浅橙底 + 深棕标题/按钮（浅色模式），超期提醒用红色系
- 运单分组详情页对齐新稿：横向统计条、紫色组规则面板、「提醒与待处理」+ 运单表（状态徽章、日期控件、详情操作）

### 新增

- 运单分组规则 `SINGLE_IN_TRANSIT_ETA_WARNING`：客户仅有一票在途时，按 ETA 提前 N 天（默认 10，可配 7）提醒到港；分组规则 UI 支持「到港前提醒(天)」；提醒卡片青绿主题 + 船舶图标

- 页面多标签：顶栏下方 Tab 栏，可同时打开多个页面（如运单管理 + 运单分组）；切换保留页面状态（KeepAlive）；标签列表写入 `localStorage`（`youzi.pageTabs`）；支持「关闭全部」（保留工作台）

- 运单分组推荐与 Excel 导入（阶段四）：`suggestions/preview|apply` API；Excel 可选列「分组编号/名称/批次号/是否最后一批」；运单列表「推荐分组」
- 分组提醒通知中心（阶段三）：顶栏铃铛聚合轨迹订阅 + 分组提醒；首页「批次提醒」面板；`GET /api/v1/shipment-group-notifications`、标记已处理 API
- 运单分组规则提醒（阶段二）：`BATCH_DELIVERY_DEADLINE`（签收 30 天期限预警/超期）、`LAST_BATCH_ARRIVED_PAYMENT`（最后一批到港催款）；表 `shipment_group_rules`、`shipment_group_notifications`；评估 API 与 `/shipment-groups` 管理页
- 运单列表分组展示与筛选：列表 `groups` 字段、`groupId`/`groupNo`/`hasGroup` 查询参数；筛选项 `groups`；批量新建/加入/移出/标记最后一批（阶段一 · 步骤 4）
- 运单分组成员 API：`POST/DELETE .../members`、`PATCH .../members/batch`（阶段一 · 步骤 3）
- 运单分组 CRUD API：`GET/POST /api/v1/shipment-groups`、`GET/PUT/DELETE /api/v1/shipment-groups/{id}`（阶段一 · 步骤 2）
- 运单分组表 `shipment_groups`、`shipment_group_members`（阶段一 · 步骤 1；设计见 `docs/design/shipment-groups-design.md`）
- 成本计算页 `/cost`：迁移 Legacy `costCalTab`（货物识别、自税 DDU、包税 DDP 多行）

### 修改

- `config/config.json` 运单查询拆为 `shipment_queryByPerson`（全量）与 `shipment_queryByOrder`（按 `odds`）；`pageNum` / `transitTimeStart` / `transitTimeEnd` 代码注入，按 `total` 自动翻页
- 计划任务新增 **DPS 运单同步**：从 DPS 拉取运单 upsert 至本地，下单时间范围可配（默认当月），批处理默认关闭
- DPS 同步字段策略：`config/shipment_dps_sync_fields.json`；`address_type` 按 `deliveryAddressType`（0=AMZ/WFS，2=3PL）
- DPS 运单同步查询参数：`orderTimeStart` / `orderTimeEnd` 改为 `transitTimeStart` / `transitTimeEnd`（发运时间）；计划任务配置字段同步更名
- 码表 · 承运商：`carrier_id` 存 DPS `carrierId` 用于反查 `carrier_code`；DPS 同步不再把 `carrierId` 写入运单 `carrier_id`（承运商单号）
- 运单列表：勾选运单「从 DPS 更新选中」，调用 `shipment_queryByOrder` upsert（`POST /api/v1/shipments/sync-from-dps`）
- 轨迹审批列表承运商列显示码表中文名（`carrierNameZh`）

- 安装 [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) 至 `.cursor/skills/`；新增规则 `.cursor/rules/youzi-v2-ui-ux.mdc`，前端 UI/UX 工作须遵循该 Skill

- 顶栏通知拆分为 **待办**（清单图标，分组提醒未处理项，支持「知道了 / 已处理」）与 **消息**（铃铛，轨迹订阅更新，支持「知道了 / 全部已读」）；分组提醒 API 增加 `scope=todo|unread`

- 运单列表筛选：新增「无邮编」（`noZipcode=true`），便于找出导入后需补全邮编的运单；导出 Excel 同步支持该筛选

- 分组提醒卡片：签收期限（橙/红 + 日历时钟图标）与整组催款（蓝色 + 钱币图标）分开展示

- 运单分组详情：分组编号与客户名分开展示，客户名用 badge；提醒卡片标题旁增加客户 badge

- 运单分组详情页：右上角「删除分组」（确认后删除分组及成员/规则/提醒，不删除运单本身）

- 客户管理：支持修改运单用户名；若该客户有关联运单，会询问是否同步更新全部运单的 `customer` 字段

- 运单列表「分组」列支持点击跳转至运单分组详情（`/shipment-groups?groupId=`）

- 自动生成分组编号格式由 `GYYYYMMDDnnn` 改为 `GYYMMDDnnn`（去掉世纪前缀 `20`，如 `G260623001`）

- 运单列表「运单号」列不再显示 VIP 五角星（客户列仍保留）

- 侧栏导航分组：支持多组同时展开；展开状态写入 `localStorage`（`youzi.navGroupsExpanded`）；当前路由所属分组强制展开且不可折叠

- 运单编辑「签收时间」改为日期时间控件（`NDatePicker type="datetime"`），与异常开始时间等字段一致

- 运单分组多类型模型：`shipment_groups.primary_type` + `shipment_group_types` 关系表；规则启用与 `groupType` 筛选按类型**交集**判断；API/前端支持 `primaryType` + `groupTypes[]`（兼容 `groupType`）

- 运单分组类型：扩展为 6 种（`PORT_BATCH` 到港批次、`PAYMENT_BATCH` 收款批次）；规则默认按类型启用（签收期限→客户/订单/手动；到港催款→船次/到港/收款/手动）；运单列表与分组管理页支持按类型筛选与编辑；`GET /api/v1/shipment-groups/meta`

- 成本计算：清空报价识别时同步重置箱数/实重/体积；DDU 表增加「派送费(RMB)」列

- 转单号前缀自动识别：`8`→FedEx、`1Z`→UPS、`15`→DPD、`C`→CWE、`0`→DHL（前后端一致）
- 全站字体栈：`Inter`、`PingFang SC`、`Microsoft YaHei`、`Noto Sans SC`；body 启用 `tabular-nums`
- 轨迹抽屉时间轴：描述 `15px/500`（`.timeline-content`），时间 `13px/#8c8c8c`（`.timeline-time`）

## 2025-06-04

### 新增

- 建立 `docs/` 文档体系：`architecture.md`、`database.md`、`deployment.md`、`api.md`、`shipment-flow.md`、`warehouse-flow.md`
- 各重要目录模块 README（`frontend/`、`backend/`、`db/`、`services/`、`schemas/`、`docs/modules/`）
- Cursor 规则 `.cursor/rules/youzi-v2-docs.mdc`：代码变更必须同步更新文档

### 修改

- 重构根 `README.md`：补充项目介绍、架构、模块列表、文档入口与开发规范
- 运单轨迹抽屉 UI：对齐设计稿（头部纵向：单号、转单号、运单状态；正文信息区含 shipment_no、可跳转 tracking_number、件数与承运商并排；承运商路由时间轴不再重复显示承运商名）
- 轨迹抽屉「承运商」字段改为 `carrierCode`，不再误用渠道 `channelNameZh`
- 全站字体栈：`Inter`、`Noto Sans SC`、`PingFang SC`、`Microsoft YaHei`（`main.css`、Naive UI、`index.html` 加载 Noto Sans SC）
- 轨迹抽屉：移除 Tracking Timeline 标题；内部/承运商 Tab 全宽均分
- 运单列表操作列：改为查看/编辑/删除图标按钮，悬停 Tooltip 显示中文（轨迹、编辑、删除）
- 运单列表订阅列：改为铃铛图标，已订阅紫色高亮，Tooltip「订阅轨迹更新」/「已订阅，点击取消」
- 顶栏右上角订阅消息铃铛：未读红点、下拉列表、全部已读；API `GET/POST /api/v1/shipment-subscriptions/notifications`
- 工作台首页：按设计稿整体布局（顶栏标题+操作、统计卡片、海运预警&ETA 提醒、关注运单/挂靠预警双栏）
- 订阅铃铛：未订阅灰色空心，已订阅紫色实心铃铛（无背景块）
- 工作台首页：增大模块间距（标题/KPI/预警/双栏/脚注），KPI 卡片栅格间距同步加大
- 工作台列表：行间分隔线改用 `--color-list-divider`；单号/港口等强调字与 delivered 高亮统一为 `rgb(70 72 212)`（`--color-accent-text`）
- 工作台 KPI 卡片：hover 仅保留上浮阴影，去掉灰色底与紫色描边
- 船期监控页：按设计稿布局（筛选栏、紫色航次横幅、挂靠时间轴表格、分页与导出）；管理操作收入「更多」菜单
- 船期横幅：加高并展示全部未到港站点；ETA 格式 `YYYY-MM-DD`；时间轴竖线跨行连续（≤25 港不分页）
- 船期挂靠列表：取消分页，表格区域内纵向滚动且滚动条常显；横幅恢复仅显示下一港
- 船期挂靠表：时间列顺序改为 ETA → ATA → ETD → ATD
- 运单轨迹新鲜度：「今日」胶囊改为浅绿色样式；「三日内」改为浅蓝色样式
- 轨迹新鲜度胶囊：浅色模式选中为实心色底+白字；深色模式选中为加深实心+白字
- 「承新于内」恢复琥珀色边框胶囊样式（选中浅色实心+白字）；有筛选时顶栏不再重复展示三组统计数字
- 顶栏世界时间：中栏网格布局、md 起显示；API 失败时用默认四城时区；秒级刷新
- 修复 Windows 保存世界时间 400：时区校验改用 ZoneInfo，并加入 `tzdata` 依赖
- 全站字体栈改为系统字体：`-apple-system`、`Segoe UI`、`PingFang SC`、`Source Han Sans`（移除 Google Fonts 与微软雅黑；统一 `constants/fonts.ts`）
- 侧栏菜单 Lucide 图标加大（20px）并加粗描边（stroke-width 2.25），视觉更圆润
- 表格操作列：轨迹 `Route`；订阅前 `BellDot`、订阅后 `BellCheck`
- 全站 Lucide 图标描边统一加大（默认 2.25，侧栏 2.75），常量见 `constants/icons.ts`
- 顶栏世界时间：去掉横向滚动条；太阳/月亮改为镂空描边图标
- 侧栏导航改为一二级菜单：工作台、报价中心、资料中心、运单中心、客户中心、数据中心、系统管理

