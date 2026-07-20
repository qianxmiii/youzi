# Youzi v2 文档中心

本目录存放面向新人、可长期维护的详细文档。代码变更时必须同步更新此处及对应模块 README。

## 目录

| 文档 | 说明 |
|------|------|
| [architecture.md](./architecture.md) | 系统架构、分层、数据流 |
| [database.md](./database.md) | SQLite 表结构、字段、ER 关系 |
| [deployment.md](./deployment.md) | 安装部署、环境变量、生产构建 |
| [api.md](./api.md) | REST API 索引与调用示例 |
| [shipment-flow.md](./shipment-flow.md) | 运单生命周期与轨迹同步 |
| [warehouse-flow.md](./warehouse-flow.md) | 仓库地址簿业务流程 |
| [SCHEMA.md](./SCHEMA.md) | 码表与字段详细说明（历史文档，与 database.md 互补） |
| [cost-calculation.md](./cost-calculation.md) | 成本计算（DDU/DDP） |
| [design/shipment-groups-design.md](./design/shipment-groups-design.md) | 运单分组与组提醒设计 |
| [design/quote-followup-management-design.md](./design/quote-followup-management-design.md) | 报价跟进管理设计 |
| [design/payment-reminder-list-design.md](./design/payment-reminder-list-design.md) | 催款列表设计 |
| [design/logistics-workbench-home-redesign.md](./design/logistics-workbench-home-redesign.md) | 物流工作台首页改版（阶段一～三已落地） |
| [MIGRATION.md](./MIGRATION.md) | Legacy → v2 迁移指南 |

## 模块 README

| 模块 | 路径 |
|------|------|
| 前端 | [../frontend/README.md](../frontend/README.md) |
| 后端入口 | [../backend/README.md](../backend/README.md) |
| 数据层 | [../db/README.md](../db/README.md) |
| 业务服务 | [../services/README.md](../services/README.md) |
| 请求/响应模型 | [../schemas/README.md](../schemas/README.md) |
| 运单域 | [modules/shipment/README.md](./modules/shipment/README.md) |
| 船期域 | [modules/vessel-schedule/README.md](./modules/vessel-schedule/README.md) |

## 文档结构规范

### 1. 根目录 `README.md`

维护：项目介绍、技术栈、系统架构、安装部署、环境变量、数据库概览、模块列表、API 入口、开发规范、更新记录索引。

### 2. 模块 `README.md`

每个重要目录必须包含：

- 模块名称与功能说明
- 主要文件及作用
- 数据结构（表 / 字段）
- API 接口（方法、参数、返回值）
- 业务流程（文字或流程图）
- 注意事项（特殊逻辑、边界、限制）

### 3. `CHANGELOG.md`

每次代码修改后按日期记录：

```markdown
## YYYY-MM-DD

### 新增
- …

### 修改
- …

### 修复
- …

### 重构
- …
```

### 4. 自动更新规则

| 事件 | 必做 |
|------|------|
| 新增功能 | 模块 README + 根 README 功能列表 + CHANGELOG；复杂功能写 `docs/*.md` |
| 修改功能 | 模块 README + 业务流程 + CHANGELOG |
| 修改数据库 | `database.md` + 表说明 + ER + CHANGELOG |
| 新增 API | `api.md` + 模块 README + 示例 + CHANGELOG |

### 质量要求

- Markdown，含目录与示例
- 与代码保持一致，禁止过期内容
- 发现文档与代码不一致时，**优先修正文档**

## 变更记录

见 [../CHANGELOG.md](../CHANGELOG.md)。
