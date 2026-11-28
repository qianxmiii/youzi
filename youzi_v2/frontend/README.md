# 前端模块（frontend）

## 模块名称

Youzi v2 前端 — Vue 3 SPA

## 功能说明

提供物流运营 Web 界面：工作台、运单管理、船期监控、地址簿、统计、客户/渠道管理、计划任务等。通过 `/api` 调用 FastAPI 后端。

右上角的眼睛用于遮挡承运商和船公司信息。打开页面时默认显示 `***`，点击可显示或再次遮挡。切换菜单沿用当前状态，刷新页面恢复遮挡。开关只控制 Youzi v2 的屏幕显示，API 权限和 Excel 导出沿用原有规则。

## 主要文件

| 路径 | 作用 |
|------|------|
| `src/main.ts` | 应用入口 |
| `src/App.vue` | 根组件 |
| `src/router/index.ts` | 路由定义 |
| `src/constants/navigation.ts` | 侧栏一二级导航（7 个中心分组） |
| `src/composables/useNavGroupsExpanded.ts` | 侧栏分组展开状态（localStorage 记忆、当前页强制展开） |
| `src/api/` | API 客户端封装 |
| `src/views/` | 页面级组件 |
| `src/components/` | 可复用组件 |
| `src/components/home/Workbench*.vue` | 工作台首页模块（Header / Focus / Todo / Arrival / RouteStatusFunnel / TransportOverview） |
| `src/api/workbench.ts` | 工作台聚合 API |
| `src/types/` | TypeScript 类型 |
| `src/domain/costCalculation/` | 成本计算纯函数（DDU/DDP、货物识别） |
| `vite.config.ts` | 构建与 `/api` 代理 |

## 路由一览

| 路径 | 页面 | 状态 |
|------|------|------|
| `/` | 工作台（明细状态分层 + 干线流程 / 今日动态 / 今日重点 / 近期到港） | ✅ |
| `/order-flow` | 订单流转（独立待办，不关联运单；销售- 待处理，其余只提示新节点） | ✅ |
| `/shipments/pre-port` | 港前运单（核对与下载；状态徽章可点击刷新明细状态；列表含收货仓、计费重列；可按收货仓筛选；「复制 → 数据」文末按客户语言追加确认句） | ✅ |
| 运单列表 · 下载 | DPS 导出（货箱/唛头/唛头重命名/拆分/自生成等）弹窗显示 **进度条 + 当前步骤**；唛头（重命名）可选字段顺序与分隔符；唛头（自生成）本地 102mm 方唛 | ✅ |
| 运单列表 · 品名 | 点击品名按 DPS 运单 ID 查看该票产品的中文品名、英文品名、箱数，并合计总箱数；与运单件数不一致时合计行高亮。勾选后可「核对件数」（最多 50 票），只列出不一致和失败 | ✅ |
| `/shipments` | 在途运单（默认筛「转运中」，可看已签收与轨迹；「复制 → 数据」与港前相同；轨迹筛选含「缺货件/预约号」：派送仓库 4 位且货件号或亚马逊预约号为空或只填了 1，可点单元格补录） | ✅ |
| `/vessel-schedules` | 船期监控 | ✅ |
| `/addresses` | 地址簿 | ✅ |
| `/customers/addresses` | 客户地址簿（客户自己的收货地址；可复制、导入导出 Excel） | ✅ |
| `/statistics` | 统计管理 | ✅ |
| `/customers` | 客户管理 | ✅ |
| `/channels` | 重定向至码表「渠道」 | → `/admin?table=channel_codes` |
| `/scheduled-tasks` | 计划任务 | ✅ |
| `/admin` | 后台管理 · 码表（渠道 tab = 完整渠道管理） | ✅ |
| `/display-settings` | 后台管理 · 显示设置 | ✅ |
| `/cost` | 成本计算（自税/包税） | 侧栏暂隐藏 |
| `/quote-center/followups` | 报价跟进 | ✅ |
| `/tools` | 工具中心（分类卡片入口） | ✅ |
| `/tools/image-link-zip` | 标签图片打包 | ✅ |
| `/tools/shipment-file-rename` | 运单文件重命名 | ✅ |
| `/tools/product-import` | 箱单转产品导入 | ✅ |
| `/tools/fba-box-code-expand` | FBA 箱号展开 | ✅ |
| `/shipments/payment-reminders` | 催款管理（侧栏待催角标、导出） | ✅ |
| `/box`、`/quote`、`/quote/batch`、`/library` 等 | 占位（待迁移）；侧栏暂隐藏箱规/单地址/批量报价/资料库 | 待迁 |

## 开发命令

```bash
cd youzi_v2/frontend
npm install      # 或 Windows: npm.cmd install
npm run dev      # http://localhost:5173
npm run build    # 输出 dist/
```

## 图标

业务 UI 图标统一使用 [Lucide](https://lucide.dev/)（`lucide-vue-next`），按名从包内 tree-shake 引入。描边宽度见 `src/constants/icons.ts`（默认 `ICON_STROKE` 2.25，侧栏 `ICON_STROKE_NAV` 2.75）；`main.css` 对 `.lucide` 有全局兜底。侧栏导航经 `NavIcon.vue` 映射 `navigation.ts` 的 `icon` 字段；表格操作见 `TableActionIcon.vue`。Naive UI 组件内置图标（下拉箭头等）仍由组件库自带。

## UI/UX 设计

前端 UI 设计与改版须遵循 Cursor Skill **ui-ux-pro-max**（`.cursor/skills/ui-ux-pro-max/SKILL.md`），规则见 `.cursor/rules/youzi-v2-ui-ux.mdc`。新页或大改版可先运行：

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "<页面描述>" --design-system --stack vue -p "Youzi"
```

## 外部运单查询（config.json）

| 配置键 | 用途 |
|--------|------|
| `dps_authorization` | DPS 共用 Bearer（运单查询、明细状态、货箱下载等） |
| `shipment_queryByPerson` | 查全部/在途运单（url 内筛选 + 自动 `pageNum`） |
| `shipment_queryByPerson_pickup` | 提货中（计划任务 DPS 提货中同步） |
| `shipment_queryByPerson_warehoused` | 已入仓（计划任务 DPS 已入仓同步；可与提货中、在途依次执行） |
| `shipment_queryByOrder` | 按运单号查（追加 `odds` + `pageNum`） |

```python
from youzi_v2.context import LOGISTICS_CONFIG_PATH
from youzi_v2.services.shipment_query_config import (
    query_shipments_by_person,
    query_shipments_by_order,
)

all_rows, _ = query_shipments_by_person(LOGISTICS_CONFIG_PATH)
by_odd, _ = query_shipments_by_order(["DPSECO260610178"], LOGISTICS_CONFIG_PATH)
```

## 注意事项

- API 基址通过 Vite 代理，无需硬编码端口
- 新页面：在 `router/index.ts` 注册 + `navigation.ts` 加菜单项
- 变更 API 调用时同步更新 `src/api/` 与 [docs/api.md](../docs/api.md)

## 相关文档

- [docs/architecture.md](../docs/architecture.md)
- [docs/api.md](../docs/api.md)

### DW 窗口

运单列表选择一票或多票，在“复制”菜单使用“复制DW”；“DW窗口设置”仍限单票。设置弹窗支持窗口模式、人工日期、只读预览和保存；修改后旧预览立即失效。复制包含每票运单明细和下一行的月日范围，票间空行，跨年不增加年份，详情展示完整日期。未选择或正在复制时禁用复制入口；批量读取限制并发、保持顺序。任一票缺少数据、过期、异常或读取失败时整批暂不复制，并列出问题供核对，不静默漏票。在“后台管理 → 码表 → 渠道”的“时效”列或操作入口配置最短至最长天数；列表显示区间，DW直接使用该区间，不再叠加提前/延后天数。

渠道时效弹窗增加“到港后送仓(天)”，默认7—15天；DW同时参考全程与ATA/ETA后的送仓范围，详情展示具体计算依据，复制渠道保留这组配置。

DW设置弹窗增加独立历史参考区，展示近90天实际/正常、近30天时效与匹配批次数；不足5个有效批次时不给出历史窗口。显示历史参考不会更改当前复制值，“填入历史窗口”先预览，需核对保存后才影响列表复制。切换运单或模式后丢弃旧请求结果；历史加载失败不阻断配置窗口。

### 独立桌面报价小窗

`src/desktopQuote/` 为独立Vue入口，复用货况识别和计费模块，提供字段显隐、人民币按kg核价、可保存汇率、美元单价和对客复制。`npm run build:quote-widget` 输出到 `../desktop_quote/build/`，不走业务站路由、不依赖后端。原生置顶、桌面快捷方式与运行环境见 [desktop_quote/README.md](../desktop_quote/README.md)。
