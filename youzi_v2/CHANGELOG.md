# 更新记录

按日期倒序记录 youzi_v2 的代码与文档变更。

## 2026-10-18

### 修改

- **工作台首页**：明细状态分层展示（摘要条、清关异常卡片）；干线进程改为 **01–08 编号卡片 + 角标色点 + 大号数字**（签收卡绿色底）；今日动态独立区块；移除「运输概览」「待处理事项」模块；**近期到港**三列分组与无船名时的标题展示优化；到港卡片深链 **运单列表**（ETA 日 + 目的港 + 船名航次）

### 新增

- **运单异常大类**：码表 `shipment_exception_codes.phase_category`（港前 `pre_port` / 港后 `post_port`）；存量类型默认港后；异常跟踪可筛大类，后台码表可维护
- **计划任务 · DPS 港前同步**：「提货中」(`shipment_queryByPerson_pickup`)、「已入仓」(`shipment_queryByPerson_warehoused`) 独立定时/手动同步，与原有 `shipment_queryByPerson` 共用发运时间范围
- **运单工作台**：侧栏「港前运单」(`/shipments/pre-port`) 与「在途运单」(`/shipments`)；按 DPS Status 划分（港前 0/01/1/4，在途 2/3）；`workspace` 与 `statusCode` 同时生效；启动时将旧码 `IN_TRANSIT`/`DELIVERED` 迁移为 `2`/`3`；港前页隐藏轨迹新鲜度与批量轨迹/明细状态同步

### 修改

- **港前运单状态**：DPS `01` 展示为「提货中」（非「已提货」）；港前列表状态徽章区分提货中（橙）/ 已入仓（青绿）/ 已下单 / 已取消
- **在途运单列表**：进入 `/shipments` 时状态筛选默认 **转运中**（DPS `2`）；工作台深链（本周签收、船名航次、明细状态漏斗等）仍不强制默认状态
- **港前运单**：筛选栏隐藏「系统视图」下拉与「快递派」勾选（时效/轨迹类筛选仅保留在在途页）；列表与列设置隐藏「承运商」「承运商轨迹」「内部轨迹」「付款状态」
- **下载货箱**：单票固定 `{运单号}_data.ext`；多票各文件重命名后装入 `{N}票数据_{时间}` 文件夹并打 `{N}票数据_{时间}.zip`
- **运单计费重**：新增 `charged_weight` / API `chargedWeight`；「更新选中运单」从 DPS 有值时写入；港前列表「邮编」后展示计费重列；港前「复制 → 数据」（独立于运单明细）为摘要 + 换行 + 计费重（英文 `Chargeweight: …kg` / 中文 `计费重: …kg`）；港前列居中加粗橙色强调
- **港前运单 · 异常**：标记异常仅可选港前大类类型；在途页仅可选港后类型
- **运单字段文案**：`originWarehouseCode` / DPS `receiveWarehouseName` 统一展示为「收货仓」（列表、表单、筛选、复制明细表头、Excel 导入导出）；旧表头「交货仓库」「起运仓」导入仍兼容
- **港前运单列表**：固定展示「收货仓」列（位于「派送仓库」前；数据来自 DPS 同步）
- **运单下载 · 进仓单**：下拉「进仓单」；按 `warehouse_entry_template.xlsx` 填充占位符（深圳仓/义乌仓 → `dps_warehouse` 收货地址）；文件名 `{N}票进仓单_{YYYYMMDD}`，不再依赖 DPS 进仓单接口
- **运单下载 · 进度**：DPS 导出（货箱/唛头/拆分/箱单等）改为异步任务 + 弹窗进度条（轮询 `/dps-export-jobs`）
- **运单下载 · 唛头（拆分）**：仅单票；输入各工厂件数（如 `1 2 2`）按 PDF 页拆分，zip `{运单号}_{总件数}ctns.zip`；段内文件 `{运单号}_{起-止}_{n}ctns.pdf`，仅 1 页时 `{运单号}_{序号}_{n}ctns.pdf`
- **港前运单**：筛选栏增加「收货仓」（`originWarehouseCode`）
- **进仓单**：明细「派送仓库/派送地址」为空时写入 **——**
- **运单下载 · 进仓单（PDF）**：下拉「进仓单（PDF）」；先按模板生成与 Excel 下载相同的 xlsx，再转 PDF；文件名 `{N}票进仓单_{YYYYMMDD}.pdf`；Windows 需 Excel + pywin32，或安装 LibreOffice（见 `docs/deployment.md`）

### 移除

- **运单下载 · 唛头（Word）**：下线 PDF→docx 下载及相关 API；依赖 `pdf2docx`、`python-docx` 已从 `requirements.txt` 移除（唛头仍用 DPS 原 PDF / 拆分 zip）

### 修复

- **进仓单 PDF**：改为「模板 xlsx → PDF」；移除 `fpdf2` 手绘版式
- **DPS 港前同步**：`queryByPerson_pickup` / `_warehoused` 改为 GET + 注入 **orderTimeStart/End**（不再误用 transitTime 导致空列表）
- **DPS 运单 Status**：同步时不再用明细 `route.status` 误判为转运中；`status_code` 更新单允许覆盖；内部轨迹同步不覆盖港前 0/01/1/4

### 修改

- **异常跟踪**：「时效状态」列与筛选项用色标区分（即将超时 / 已超时 / 严重超时及阶段卡点类型）
- **明细状态同步**：不再把 DPS 明细节点写入 `latest_tracking_*`，避免运单列表「内部轨迹」列被覆盖后显示为空
- **轨迹抽屉**：标题运单号点击复制
- **异常跟踪**：运单号左固定；「跟进状态」与「操作」一并右固定，横向滚动宽度按列宽合计，避免跟进列被操作列遮挡
- **异常跟踪**：「有无异常」改为「仅异常货件」勾选；默认未选（无当前异常码货件），勾选后只显示有异常码货件
- **异常跟踪**：列表新增「明细状态」列（与运单列表色标一致，数据来自预警关联运单 `route_status`）
- **异常跟踪**：行内「已跟进 / 已解决 / 转异常 / 忽略」合并为悬停下拉，按钮默认展示「已跟进」（已跟进态带次数）
- **工作台**：「今日动态」保留离港/到港/内签收/异常，并增加到中转仓、快递交仓、轨迹签收（601）共 7 项
- **工作台**：右上角刷新改为胶囊按钮并带说明；静默刷新时显示「更新中」与成功提示，不再无反馈
- **DPS 明细状态同步**：回写 `route_last_mile_handover_time`、`route_track_signed_time`；运单列表可按明细节点时间筛选
- **运单列表**：支持 URL 深链 `atdFrom`/`ataFrom`、`hasException`+`timeField=exceptionOpenedTime`、明细节点 `timeField`

## 2026-10-17

### 新增

- **运单管理 · 下载**：下拉「货箱 / 唛头 / 箱单发票 / 排仓单」；排仓单 `dps_warehouseform_download` 为 **POST + `?ids=`**（逗号拼接 waybillId，**每批最多 50**，超出自动多批请求后 zip）；单票 `{运单号}_排仓单.ext`
- **运单管理 · 下载**：箱单发票 `dps_packinglist_download` 为 **POST + `?ids=`**（多票逗号拼接），单票 `{运单号}_箱单发票.ext`，多票 DPS 原名

### 修改

- **承运商轨迹**：`vendors` 主项可配置 `fallbackVendor` / `fallbackVendors`；主系统无轨迹时按序尝试备用（如SENLEI → SENLEI2）
- **顶栏世界时间**：时区较多时改为横向滚动展示，避免末个城市时间被裁切
- **DPS 配置**：`shipment_queryByPerson` / `shipment_queryByOrder` / 明细状态 / 货箱下载等共用根级 **`dps_authorization`**（仍兼容各块内 `Authorization`）；缺省时接口返回 503 而非无响应；裸 token 自动补 `Bearer `
- **开发代理**：Vite `/api` 代理超时与 DPS 长同步对齐（10 分钟），减少 `Failed to fetch`
- **统计管理 · 运输时效**：页头右上角「刷新」重新拉取筛选项与当前条件下的分析/明细
- **统计管理 · 运输时效**：渠道/承运商全程时效排行、分组及「承运商 × 渠道」表展示码表中文名（无则回退 code）
- **统计管理 · 运输时效**：任一段异常持续超过 7 天则该票不计入海运/全程/到港后送仓时效样本（明细可标记「异常期超7天(不计入时效)」）
- **异常跟踪**：「到仓未派送」时效预警在明细 **509 卡派已约仓** 时展示为 **约仓未派送**（预警类型仍为 `DEST_WAREHOUSE_NO_DISPATCH`）
- **DPS 明细状态同步**：轨迹含 301/306 且本地 ATD/ATA 为空时，按节点最早 `nodeTime` 回写 `atd`/`ata`（不覆盖已有值）
- **异常跟踪**：待办退出条件与运单「已签收」对齐——粗状态 `DELIVERED` 或有 `delivered_time` 时关闭时效预警（仍保留明细 `TRACK_SIGNED` 判定；卡点起算仍用明细节点时间）
- **运单管理 · 复制**：「运单明细 / 转单号 / 最新轨迹」合并为一条「运单明细」（含关联单号、客户编号、货件号）；关联单号与货件号相同只显示一处；去掉「运单明细（关联单号）」菜单项
- **运单管理 · 复制**：去掉下拉「运单号 / 关联单号」纯号码项；主按钮仍默认复制运单号（换行），明细等走悬停下拉
- **运单管理 · 复制**：「运单明细」等 `=` 拼接文案以运单号开头
- **明细状态**：新增 DPS `509` → `TRUCK_DISPATCH_APPOINTED`（卡派已约仓）；启动时码表幂等同步，列表/抽屉徽章与筛选可用
- **运单列表状态列**：粗状态 `DELIVERED`（如 DPS 签收时间或内部轨迹 API `status=3`）时优先显示「已签收」，不再被明细 `TRACK_SIGNED`（轨迹签收）顶替；轨迹抽屉标题徽章与列表规则一致

## 2026-10-16

### 新增

- **企业微信 · 订阅更新推送**：运单订阅后内部/承运商轨迹变更、ETA 到港每日提醒与顶栏铃铛同源写库时，主动推送到 `wecom_webhook.chat_id`（`subscription_push_enabled` 默认随企微启用）
- **企业微信通知**：`services/wecom_webhook.py` + `POST /api/v1/notifications/wecom/test`；支持 Webhook（`key`/`url`）与智能机器人长连接（`bot_id`+`secret`+`chat_id`，见文档 101463）

### 修改

- **企业微信配置**：`bot_id`+`secret` 时默认可用（无需 `enabled`）；主动推送须配置 `chat_id`
- **企业微信长连接**：后端启动自动连 WebSocket；群内 @机器人 后 `chat_id` 写入 `logs/wecom-aibot-*.log`；常驻模式下发送仅走守护连接（不再临时连以免踢线）
- **企业微信 @ 查运单**：解析消息中的 DPSECO 运单号，查询本地运单并 stream 回复状态摘要（`shipment_query_enabled` 默认 true）

### 修复

- **企业微信 @ 查运单**：`get_database()` 补全 `youzi_v2/data/youzi_v2.db` 路径，避免查单报错

### 修改

- **企业微信 @ 查运单**：回复扩展客户/货件/渠道/仓库/转单号等；查单前默认同步 DPS 明细状态 + 内部/承运商轨迹（`shipment_query_refresh`）；客户编号与货件号相同时只显示货件号；内外轨迹与时间分行展示；空字段整行省略；支持运单号/货件号/客户编号查询（优先级依次匹配）；消息含「明细」时返回与列表「复制 → 运单明细」相同摘要（`services/shipment_copy_format.py`），且跳过查单前 DPS/轨迹同步

### 文档

- 新增 [docs/wecom-aibot.md](./docs/wecom-aibot.md)（企业微信智能机器人专篇）；索引同步 `docs/README.md`、根 README、`deployment.md`、`api.md`、`services/README.md`

## 2026-10-13

### 新增

- **轨迹抽屉 · 明细状态**：运单号右侧徽章展示明细状态；点击按 `waybillId` 轻量更新并刷新（修复未包 `NDrawerContent` 导致标题不显示）
- **运单管理 · 状态列**：点击状态徽章可对该单刷新明细状态（需已有 `waybillId`）

### 修改

- **异常跟踪**：签收判断改为明细状态 `TRACK_SIGNED`（不再用粗状态 `DELIVERED` / `delivered_time`）；到港未送仓另认 `LAST_MILE_HANDOVER` 为已送仓；明细状态同步到签收后立即关闭预警
- **异常跟踪 · 阶段卡点**：起算改用明细状态节点时间——入库未开船=`202`、到港未送仓=`306`、新增到仓未派送=`502`（超 5 天未交仓/签收）；同步回写 `route_warehouse_in_time` / `route_arrived_pod_time` / `route_dest_transit_warehouse_time`

## 2026-10-12

### 修改

- **快递派查价**：按最新价卡核对四渠道——美森正班（限时达非定提）、美森加班（特快达）、合德以星（快速达非定提，深圳/义乌五档已更新）、普船（经济达，两地同价维持）
- **快递派查价 · 更新时间**：`expressPricing.updatedAt` 记录价目日期，并在查价 Tab 顶部显示「价格更新：YYYY-MM-DD」（改价时同步改该字段）
- **运单管理 · 复制**：「转单号」改为原「运单明细」格式（`运单号 = 货件号 = 仓库 = Nctns` + 可选第二行 `-- 承运商 转单号`）；「运单明细 / 运单明细（关联单号）」不再附带转单号行
- **工作台首页 · 明细状态**：移到页头下方最上方；改为色条指标格（上标签下数字），去掉嵌套徽章

## 2026-10-10

### 新增

- **明细状态同步**：按 `waybillId` 调用 `config.dps_route_status_query` 轻量回写 `route_status`；运单管理「更新选中/全部明细状态」；计划任务「更新全部明细状态」（`POST .../sync-route-status-from-dps`、`.../run-dps-route-status-sync`）；接口 URL 仅存 config.json

### 修改

- **文案**：原「细状态」统一为「明细状态」（筛选、码表、按钮与文档）
- **工作台首页**：增加未签收「明细状态」漏斗，点击节点跳转运单管理（`routeStatus` / `missingRouteStatus` + `notDelivered`）
- **运单文件重命名**：Excel 无仓库代码时用邮编拼文件名；表头可仅有邮编列；递归扫描所选文件夹下全部子目录

## 2026-10-07

### 新增

- **运单轨迹明细状态 `route_status`**：映射 DPS `commerceWaybillRouteInfo.status`（码表 `shipment_route_status_codes`）；列表可筛选/展示；同步时允许覆盖回退
- **设计说明**：`docs/design/shipment-route-status-design.md`

### 修改

- **DPS 粗状态**：仅 `signingTime`→`DELIVERED`；不再因 601 / `markVos` / nodeDesc「signed」判签收（601→明细状态 `TRACK_SIGNED`；510→`LAST_MILE_HANDOVER`）
- **运单列表状态列**：优先显示明细状态中文名，无明细状态时回退粗状态（鼠标悬停可见粗状态）；各明细状态用不同色标区分
- **信息传递（DPS 100）**：非关键节点——不同步写入 `route_status`、筛选隐藏、列表回退粗状态
- **清关异常联动**：DPS 明细状态 206/402 自动标记「出口海关异常 / 进口清关异常」；最新关键节点离开这两类后自动解除（不覆盖掉件等人工异常）

## 2026-09-28

### 新增

- **工具中心 · FBA 箱号展开**：按「前缀 箱数」批量生成 `前缀+命名符+序号`（命名符默认 `U`，尾数默认 6 位），支持一键复制

## 2026-09-24

### 新增

- **轨迹转单号回写**：内部轨迹含 `FedEx/UPS/DHL… + 合法单号` 时，若运单转单号为空则自动写入（不覆盖已有值；多条命中取事件时间最新一条；可顺带填空 `express_code`）

### 修改

- **快递派查价 · 美森正班（限时达-洛杉矶非定提）**：按最新价卡上调深圳/义乌五档分区单价
- **快递派查价 · 美森加班（特快达-洛杉矶）**：按最新价卡上调深圳/义乌五档分区单价

## 2026-09-22

### 修改

- **异常跟踪 · 到港未送仓**：由 ATA 后 12 天改为**超过 5 天**再提示（第 6 天起；截止日 = ATA + 5）

## 2026-09-21

### 修改

- **侧栏菜单**：暂时隐藏未迁移项「箱规计算」「单地址报价」「批量报价」「资料库」，以及「成本计算」「旧版后台」（路由/旧站仍可直达）
- **渠道管理**：后台码表「渠道」tab 嵌入原渠道管理页（含时效、全量导入）；侧栏「系统管理 → 渠道管理」移除；`/channels` 重定向至 `/admin?table=channel_codes`
- **侧栏**：「显示设置」从后台管理移到「系统管理 → 设置」下


## 2026-09-19

### 修改

- **异常跟踪 · 运输时间列**：起运/到港改为天蓝字、截止日改为琥珀字，避免原先灰字对比度不足
- **轨迹时间回写 · ATD**：英文 `The train has departed` 视为离港节点（与 `The goods have been shipped` / 「已开船」「已离港」同为无显式 ATD 时的兜底）
- **异常跟踪**：列表排序改为未跟进在前、**已跟进整组排最后**（组内仍按严重超时 / 已超时 / 即将超时）

## 2026-09-18

### 新增

- **异常跟踪**：批量勾选后可「更新选中内部轨迹」（复用运单 `sync-tracking`，按运单号去重）

### 修改

- **催款管理**：默认「待催」与侧栏/摘要的 `todoCount`、`overdueCount` **排除月结**（仍可在「全部未付款」或结算方式筛「月结」查看）；列表排序改为**已跟进排最后**
- **运单管理 · 外露筛选**：去掉「时间口径」与日期区间（改到高级筛选）；外露增加「渠道大类」「是否有异常」「快递派」（有转单号）
- **运单管理 · 运单号**：点击即可复制，不再弹出 tooltip；列表加粗保留
- **运单管理 · 复制**：「运单明细」为 `运单号 = 货件号 = 仓库 = Nctns` 换行 `-- FedEx 转单号`（无转单号则省略第二行）；「运单号」与默认「复制」仍为纯号码换行
- **运单管理 · 筛选**：仅「多号精确搜索」（≥2 个单号）时放开状态；单号及其他筛选仍保留默认「转运中」

## 2026-09-17

### 修改

- **快递派查价 · 普船（经济达-洛杉矶）**：按最新价卡更新 `data/data_price.js`；华南（深圳）与华东（义乌）12/21/45/71/101 五档分区单价对齐，两地同价
- **快递派查价 · 合德以星（快速达-洛杉矶定提）**：按最新价卡更新深圳/义乌五档分区单价（义乌略高于深圳）
- **快递派查价 · 美森加班（特快达-洛杉矶）**：按最新价卡更新深圳/义乌五档分区单价（深圳略高于义乌）
- **快递派查价 · 美森正班（限时达-洛杉矶非定提）**：按最新价卡更新深圳/义乌五档分区单价（深圳略高于义乌）

## 2026-09-05

### 新增

- **渠道管理 · DPS渠道名**：`channel_codes.dps_channel_name`（API `dpsChannelName`），用于将 DPS `channelCode`/`channelName` 映射到本地渠道编码；DPS 运单同步时自动反查写入

### 修改

- **渠道种子全量替换**：按「渠道清单.xlsx」导入约 105 条（`code`=表格 code，`name_zh`/`dpsChannelName`=cnName，`name_en`=name）；`seed-defaults` 改为**先清空再导入**，并尽量把运单英文渠道名映射到新 code；重复 code 保留表格最后一条

## 2026-08-26

### 修复

- **工具中心 · 运单文件重命名**：Excel 解析支持多工作表（封面页 +「运单信息」）、`.xls` 老格式、表头换行/括号说明；前端展示后端 `detail` 错误文案

## 2026-08-22

### 修改

- **单地址报价 · 派送费**：报价文本按填写币种原样显示（填 RMB 显示 RMB，填 USD 显示 USD），不再随报价格式折算；总费用折算逻辑不变

## 2026-08-18

### 修改

- **运单管理**：勾选后选择栏除条数外，同时显示选中件数合计
- **催款管理**：客户单号后新增「关联单号」列（`ref_shipment_no`）；Excel 导出同步增加该列
- **单地址报价 · 超长/超尺寸/超重**：渠道为 Air express 时默认单价改为超长·超尺寸 200RMB=30USD、超重 280RMB=42USD；其它渠道仍为 150/21、180/25。切换渠道时若输入仍是默认档会自动同步。

## 2026-08-17

### 新增

- **单地址报价 · 超长费**：超尺寸左侧增加「超长」选项（单价默认 150 RMB/箱，USD 按 150:21 换算，结构与超尺寸相同）；报价文本写入「超长费 / OverLength fee」；历史表新增 `is_overlength` / `overlength_fee` / `overlength_quantity`

### 修改

- **单地址报价**：隐藏承运商下拉（DOM 保留，不影响分泡等逻辑）
- **单地址报价 · MOQ Box**：增加单位下拉（kg / cbm，默认 kg）；报价格式名含 `RMB` 时输出中文「单箱最低计费重为…kg / 单箱最低计费方为…cbm」，否则英文 `MOQ each box is …`

### 修复

- 超尺寸中文报价文案由误写的「超长费」改为「超尺寸费」

## 2026-08-13

### 新增

- **工具中心 · 箱单转产品导入**：上传箱单发票生成产品导入模版（`/tools/product-import`；API `POST/GET /api/v1/tools/product-import*`）；设计见 `docs/design/tools/product-import-design.md`
- **单地址报价 · 派送费**：提货费右侧增加派送费（可勾选，支持 USD / RMB 输入）；计入报价文本总费用与综合单价；报价历史表新增 `has_delivery_fee` / `delivery_fee_rmb` / `delivery_fee_usd`

## 2026-08-12

### 新增

- **工具中心 · 运单文件重命名**：导入 Excel（运单号/国家/仓库代码/件数），选择本地文件夹，将 `运单号.ext` 重命名为 `运单号-国家-仓库代码-件数.ext`（Chrome/Edge；设计见 `docs/design/tools/shipment-file-rename-design.md`）
- **运单文件重命名**：可选列「文件夹名」；有值时相同文件夹名的文件归入同一子目录

### 修改

- **异常跟踪 · 入库未开船**：改为入库超过 7 天（第 8 天起）才生成提示；截止日仍为入库日 + 7

## 2026-08-11

### 修改

- **轨迹时间回写 · ATD**：无显式 `ATD` 字段时，除英文 `The goods have been shipped` 外，轨迹含「已开船」「已离港」也视为开船节点并回写 ATD（取最早匹配轨迹的事件时间）

## 2026-08-08

### 修改

- **异常跟踪**：标题下「异常 / 即将超时 / 已超时 / 严重超时」改为可点选筛选 badge（与时效状态下拉联动；再点可取消）

## 2026-08-06

### 修改

- **异常跟踪**：新增独立列「超时天数」（`+N 天` / `-N 天`，绿/橙/红着色，表头悬停说明），置于「时效状态」前；时效状态列仅保留类型 + 风险标签
- **异常跟踪**：ATD / ATA / 截止日合并为「运输时间」列（表头副标题「起运 - 到港 / 截止日」；单元格日期加粗、`~` 浅色分隔 + 灰字「截止 MM-DD」；悬停仍见完整年月日）；「入库时间」仍为独立列（MM-DD）

## 2026-08-05

### 修改

- **异常跟踪**：待办列表同运单只显示最严重一条（严重超时 > 已超时 > 即将超时；同级时阶段卡点优先于运输时效）；悬停可见合并的类型；跟进/解决会一并处理关联预警
- **顶栏待办 / 运输时效**：止血与防堆积
  - 扫描时：先重绑换 ID 的运单预警 → 关闭真正孤儿 → 同运单号同类型去重（只留最新）
  - `event_key` 改为优先用运单号，避免删建运单重复开预警；有 ATD/ETD 仍自动关闭「入库未开船」
  - 顶栏待办按运单合并展示，角标按运单去重；卡片展示多类型标签
  - 「知道了」改为「稍后再说」（仅已读）；支持本页批量已跟进；分组提醒同组同规则同运单未处理不重复插入
  - 新增 `POST .../batch-follow-up`、`batch-resolve`

## 2026-08-04

### 新增

- **运单**：`ref_shipment_no`（关联单号，DPS `assOrderNumber`）；设计见 `docs/design/ref-shipment-no-design.md`
- 历史回填脚本：`python youzi_v2/scripts/migrate_ref_shipment_no.py`（按单号重拉 DPS；查不到不改）

### 修改

- DPS 映射：`customer_no` 改为仅取 `internalOrderNum`（不再优先 `assOrderNumber`）
- 运单列表 / 表单 / 批量编辑 / Excel / 复制明细：增加「关联单号」；多号搜索与客户编号筛选同时匹配 `customer_no` 与 `ref_shipment_no`
- 异常跟踪 / 催款管理：标题下显示摘要统计（待办/待催、超时或逾期、当前列表条数）
- 异常跟踪「立即扫描」改为主色按钮 + 扫描图标
- 催款管理导出：增加「ATA」「签收日期」列（日期格式 `YYYY-MM-DD`）
- 轨迹抽屉信息区新增「派送仓库」「邮编」（同一行）
- **订阅到港提醒**：已订阅运单在 ETA 前 7 天起至签收前，每天向顶栏消息铃铛推送一条（设计见 `docs/design/subscription-eta-daily-reminder-design.md`）
- 运单导出：承运商列优先输出码表中文名；新增「转单号」「品名」列（品名在供应商后；内部轨迹时间/内容为末两列）；船期列为 ETD / ATD / ETA / ATA（日期格式同 ATD）
- 运单复制：下拉增加「关联单号」；「运单明细（关联单号）」在客户编号前插入关联单号；`=` 拼接时跳过空字段
- **运单管理**：Excel 导出增加「供应商」列（`supplier_name`）；复制运单明细列顺序同步
- **运单管理**：去掉「已付款不可修改」锁定；已付款运单可正常编辑、批量改字段、DPS upsert 覆盖其它字段（付款状态仍按既有回填规则：本地已付款不被 DPS 未付款覆盖）

## 2026-08-03

### 修改

- **催款管理**：与运单列表一致，默认排除整柜；筛选栏增加「整柜」checkbox（默认不选中=排除，勾选=仅整柜）；列表 / 导出 / 摘要 / 侧栏角标均支持 `fclOnly`

### 修复

- **成本计算 · 自税 DDU 单价/kg**：改为按计费重（`max(实重, 体积×10⁶/6000)` 向上取整）计算，修复泡货（实重/方数小于 167）仍按实重除导致单价偏高的问题；与包税口径一致。货况条与卡片副标题展示计费重。

## 2026-08-03

### 新增

- 催款管理：勾选运单后支持「更新选中运单」（与运单管理相同，调用 DPS `shipment_queryByOrder`）

## 2026-07-21

### 新增

- **工具中心**：按 `docs/design/tools/tools-center-design.md` 落地
  - 路由 `/tools`；侧栏「常用工具」仅保留「工具中心」入口
  - 工具注册表 `constants/toolsRegistry.ts`；卡片分类进入各工具页
  - 首期工具「标签图片打包」仍走 `/tools/image-link-zip`（异步任务 + 进度）
  - 设计文档：`design/tools/image-link-zip-design.md`

## 2026-07-20

### 新增

- **常用工具 · 标签图片打包**：上传 Excel，读取 P 列（可改）图片链接批量下载并打 zip；侧栏「常用工具」入口 `/tools/image-link-zip`；异步任务 API（进度轮询 + 下载）`/api/v1/tools/image-link-zip/jobs*`

### 修改

- 工作台首页 UI：对齐全局 `--color-*` token 与其它页面布局（全宽、`gap-4`、`section-h2`）；强化今日重点卡 / 待办行 / 到港行 hover·focus，数字 tabular-nums，兼容暗色与 `prefers-reduced-motion`

## 2026-07-18

### 新增

- **工作台首页改版（阶段一～三）**：紧凑页头 → 今日重点 → 待处理事项+近期到港 → 运输概览
  - API：`GET /api/v1/workbench/overview`（`focus` / `todos` / `arrivals` / `overview`，模块级容错）
  - 前端：`HomeView` 拆分为 `WorkbenchHeader` / `FocusMetrics` / `TodoList` / `ArrivalTimeline` / `TransportOverview`
  - 深链：催款 `?scope=todo`；运单 `hasAta`/`notDelivered`、`deliveredFrom`/`deliveredTo`、`vesselVoyage`

### 修改

- 侧栏：将「显示设置」从系统管理移入「后台管理」分组（与码表并列）
- 工作台 KPI 卡片新增「查验中」：按运单当前异常 `exception_code=INSPECTION`（查验中）计数，点击跳转运单列表

## 2026-07-17

### 修复

- 内部轨迹手动同步：接口返回重复节点时不再因 UNIQUE 约束 500；`replace_for_shipment` 按 (时间, 描述) 去重后再写入

## 2026-07-15

### 新增

- 催款管理：侧栏「催款管理」待催数量角标；标题下展示待催 / 全部未付款 / 逾期 / 当前列表条数；支持按当前筛选导出 Excel
- API：`GET /api/v1/shipments/payment-reminders/summary`、`GET /api/v1/shipments/payment-reminders/export`

### 修改

- 运单导出 Excel：新增「签收时间」「ATD」列（仅导出不导入）；导出值只保留日期（`YYYY-MM-DD`）

## 2026-07-13

### 新增

- **报价跟进（首版）**：按 `quote-followup-management-design.md` 实现
  - 表 `quote_opportunities` / `quote_versions` / `quote_followups`；API `/api/v1/quote-opportunities*`
  - 页面 `/quote-center/followups`（报价中心菜单）；支持新增、跟进、调价版本、成单/丢单/取消/延期
  - 顶部待办铃铛聚合「今日 / 逾期 / 即将过期」数量

### 修改

- DPS 同步：客户单号 `customer_no` 优先 `assOrderNumber`，为空时回退 `internalOrderNum`
- 催款管理：筛选增加「未跟进 / 已跟进」（API `followupStatus=unfollowed|followed`）
- 催款管理：整柜渠道运单「运单号」列展示提单号、「客户单号」列展示柜号；API 增加 `billOfLadingNo` / `containerNo` / `isFcl`

### 修复

- 运单编辑：已付款改为未付款时，编辑表单提交全部字段会 400；现允许在请求中仅生效「改回未付款」，表单对已付款单锁定其它字段

## 2026-07-14

### 修复

- 已付款运单：允许同步内部轨迹摘要、状态（含 DELIVERED）及轨迹时间回写（签收时间等）

## 2026-06-18

### 修改

- 渠道管理列表增加 **时效** 列，展示默认运输时效规则（ATD + 预估天数）；未配置显示「—」，点击可打开时效配置
- 异常跟踪：「剩余/超期」与「风险」合并为 **时效状态** 列（标签 + 剩/超天数，悬停显示截止日）；人工异常标识移至 **运单号** 后（与运单列表一致）；筛选栏「风险等级」改为 **时效状态**（即将超时 / 已超时 / 严重超时 / 入库未开船 / 到港未送仓），阶段类通过 `alertType` 查询；运单号悬停显示复制按钮；已解除异常仍于「已运输天数」括号内展示历史异常时长（悬停提示「曾发生异常」）
- 运单编辑：承运商改为下拉选择（显示码表中文名，保存 `carrier_codes.carrier_id` 至 `carrier_code`）
- 轨迹抽屉：异常信息（含历史记录）移至路由轨迹上方展示
- WY 承运商：`apiUrl` 一次 POST `customerOrderNumberList` 查轨迹；`systemOrderNumber` 回写运单承运商单号（`carrier_id`）
- 异常跟踪扫描对齐设计文档：新增 **入库未开船**（入仓 7 天无 ETD/ATD）、**到港未送仓**（ATA 10 天未签收）两类预警；全程运输超时仍按 ATD + 渠道预估天数；各类型独立 `event_key` 与关闭逻辑

### 修复

- 异常跟踪：默认列表仅展示**未签收**且预警状态为 `open`/`acknowledged` 的待办；勾选「含已签收/历史」后 `scope=all` 查看全部
- 异常跟踪：已签收运单的**已运输天数**改为 **签收日 − ATD**（历史视图）；未签收仍为 **今天 − ATD**
- 签收判定：`delivered_time` 非空或 `status_code=DELIVERED` 即视为已签收（有签收时间但状态仍为转运中也算已签收）
- 签收后自动关闭：写入签收时间/状态变更、轨迹回写、扫描兜底时，将 `open`/`acknowledged`/`converted` 预警置为 `resolved`，并关闭异常跟进待办
- 异常时长展示统一为**自然日天数**（如 `64天`），不再换算成「X月X天」；异常跟踪已运输天数列括号内同步
- 内部轨迹同步：`Your goods are in the warehouse` 入仓占位节点重新写入轨迹表并在抽屉中展示；运单列表「最新轨迹」摘要仍跳过该占位文案

- 待办/提醒弹框：带字母前缀的运单号（如 `DPSECO260225010`）不再被拆成仅高亮数字部分，完整单号作为一体展示
- 异常跟踪页：筛选栏改为单行横向滚动（`min-w-0` + 可横向滚动），新增渠道筛选；「处理状态」列固定右侧，避免被挤出视口

- 运单分组规则评估：`BATCH_DELIVERY_DEADLINE` 使用未定义变量 `now` 导致整组评估失败，连带 `GROUP_ARRIVED_PAYMENT` 无法触发；各规则独立捕获异常，互不影响

- 轨迹同步（内部/承运商、含定时任务）完成后，对本次有更新的运单所在分组自动评估提醒；同步响应增加 `groupAlertsEvaluated` / `groupAlertsCreated`

- 分组详情「组内提醒」触发时间误显示为 JSON 对象；改为相对时间展示，悬停显示精确时间
- 分组预警卡片统一配色：浅橙底 + 深棕标题/按钮（浅色模式），超期提醒用红色系
- 运单分组详情页对齐新稿：横向统计条、紫色组规则面板、「提醒与待处理」+ 运单表（状态徽章、日期控件、详情操作）

### 新增

- **异常跟踪（首版）**：按 `shipment-exception-tracking-design.md` 实现运输时效预警
  - 表 `channel_sla_rules`、`shipment_sla_alerts`；渠道管理「时效」配置（ATD + 预估天数）
  - 每日计划任务扫描 + 轨迹同步后单票重算；优先 `expected_delivery_time`，否则 `ATD + 预估天数`
  - 页面 `运单中心 / 异常跟踪`：筛选、标记已处理、忽略、转人工异常（默认运输超时）；列表展示已运输天数、渠道预估时效
  - 工作台摘要卡片 + 顶栏待办（已超时/严重超时待处理）
  - 新增异常类型码 `TRANSIT_TIMEOUT`（运输超时）

- 运单列表复制菜单增加「运单明细」：`运单号 = 货件号 = 派送仓库（空则邮编）= 件数ctns`；移除原 Excel 宽表复制项


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

- 运单表新增 **入仓时间**（`warehouse_entry_time`）：内部轨迹同步后，由 `Your goods are in the warehouse` 节点事件时间自动回写（取最早一条）；运单列表列配置与编辑表单可查看/修改
- 运单列表：渠道筛选项与摘要显示中文名；运单号列默认更宽
- 运单列表筛选与列配置对齐 `docs/design/shipment-list-filter-design.md`：顶部多号精确搜索 + 轨迹搜索；关键词/分号码批次迁入高级筛选；默认列更新；后端号码精确 IN 匹配
- 异常跟进待办文案去掉分档间隔说明（如「≥10 天每 5 天」「当前每 7 天需跟进一次」）；API 返回时统一格式化，历史待办即时生效
- 异常跟进卡片固定鼠尾草绿主题 `#6d9c79`（不再因 urgent 级别显示红色）
- 工作台待办提醒合并异常跟进（与顶栏待办一致）；异常跟进卡片采用 `#6d9c79` 独立配色
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

