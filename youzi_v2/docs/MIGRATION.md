# 迁移指南

## 仓库策略

**所有活跃开发仅在 `youzi_v2/`。** 根目录的 `index.html`、`js/`、`server/` 等为 Legacy，将逐步删除；新代码勿再写入那些路径。

## 原则

1. **一次迁一个路由**，迁完再在侧栏去掉「待迁」徽章。
2. **业务逻辑**放进 `frontend/src/domain/`（纯 TS），页面只负责 UI。
3. **持久化**一律走 FastAPI，不再新增 localStorage 业务数据。
4. 旧版 `index.html` 保持可用，直到该模块在新站验收通过。

## 推荐顺序

1. **地址簿** `/addresses` — 已有 CRUD API，适合练手
2. **箱规** `/box` — 从 `logistics.js` 抽 `calculate`、`parseDimensions`
3. **单地址报价** `/quote` — 依赖箱规导入与 `updateQuote`
4. **报价历史** — 嵌入 quote 页或 admin
5. 批量报价、资料库、运单监控（**成本计算** 已迁至 `/cost`）

## 单模块步骤模板

```text
1. 在 frontend/src/domain/ 提取纯函数 + Vitest（可选）
2. 新建 views/<module>/XxxView.vue + 子组件
3. 用 ofetch 接现有 /api/*
4. 路由 meta.migration 删掉，侧栏 badge 去掉
5. 在 DOCS.md / README 更新状态
```

## 样式约定（Linear / Vercel）

- 背景 `#09090b`，面板 `#18181b`，边框 `#27272a`
- 字体 Inter，正文 15px
- 主按钮：白底黑字；强调色 violet `#8b5cf6`
- 复用 `panel`、`glass-header`、`nav-item` 工具类（`assets/main.css`）
