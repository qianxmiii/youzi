# 前端模块（frontend）

## 模块名称

Youzi v2 前端 — Vue 3 SPA

## 功能说明

提供物流运营 Web 界面：工作台、运单管理、船期监控、地址簿、统计、客户/渠道管理、计划任务等。通过 `/api` 调用 FastAPI 后端。

## 主要文件

| 路径 | 作用 |
|------|------|
| `src/main.ts` | 应用入口 |
| `src/App.vue` | 根组件 |
| `src/router/index.ts` | 路由定义 |
| `src/constants/navigation.ts` | 侧栏一二级导航（7 个中心分组） |
| `src/api/` | API 客户端封装 |
| `src/views/` | 页面级组件 |
| `src/components/` | 可复用组件 |
| `src/types/` | TypeScript 类型 |
| `src/utils/` | 工具函数 |
| `vite.config.ts` | 构建与 `/api` 代理 |

## 路由一览

| 路径 | 页面 | 状态 |
|------|------|------|
| `/` | 工作台（海运预警） | ✅ |
| `/shipments` | 运单管理 | ✅ |
| `/vessel-schedules` | 船期监控 | ✅ |
| `/addresses` | 地址簿 | ✅ |
| `/statistics` | 统计管理 | ✅ |
| `/customers` | 客户管理 | ✅ |
| `/channels` | 渠道管理 | ✅ |
| `/scheduled-tasks` | 计划任务 | ✅ |
| `/admin` | 码表管理 | ✅ |
| `/box`、`/quote` 等 | 占位（待迁移） | 待迁 |

## 开发命令

```bash
cd youzi_v2/frontend
npm install      # 或 Windows: npm.cmd install
npm run dev      # http://localhost:5173
npm run build    # 输出 dist/
```

## 图标

业务 UI 图标统一使用 [Lucide](https://lucide.dev/)（`lucide-vue-next`），按名从包内 tree-shake 引入。描边宽度见 `src/constants/icons.ts`（默认 `ICON_STROKE` 2.25，侧栏 `ICON_STROKE_NAV` 2.75）；`main.css` 对 `.lucide` 有全局兜底。侧栏导航经 `NavIcon.vue` 映射 `navigation.ts` 的 `icon` 字段；表格操作见 `TableActionIcon.vue`。Naive UI 组件内置图标（下拉箭头等）仍由组件库自带。

## 注意事项

- API 基址通过 Vite 代理，无需硬编码端口
- 新页面：在 `router/index.ts` 注册 + `navigation.ts` 加菜单项
- 变更 API 调用时同步更新 `src/api/` 与 [docs/api.md](../docs/api.md)

## 相关文档

- [docs/architecture.md](../docs/architecture.md)
- [docs/api.md](../docs/api.md)
