# 更新记录

按日期倒序记录 youzi_v2 的代码与文档变更。

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
