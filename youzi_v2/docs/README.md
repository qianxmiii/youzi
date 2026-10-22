# Youzi v2 文档中心

本目录存放面向新人、可长期维护的详细文档。代码变更时检查并更新受影响的文档与模块 README。

## 目录

| 文档 | 说明 |
|------|------|
| [architecture.md](./architecture.md) | 系统架构、分层、数据流 |
| [database.md](./database.md) | SQLite 表结构、字段、ER 关系 |
| [deployment.md](./deployment.md) | 安装部署、环境变量、生产构建 |
| [wecom-aibot.md](./wecom-aibot.md) | 企业微信智能机器人（长连接、@ 查运单、主动推送） |
| [api.md](./api.md) | REST API 索引与调用示例 |
| [shipment-flow.md](./shipment-flow.md) | 运单生命周期与轨迹同步 |
| [warehouse-flow.md](./warehouse-flow.md) | 仓库地址簿业务流程 |
| [SCHEMA.md](./SCHEMA.md) | 码表与字段详细说明（历史文档，与 database.md 互补） |
| [cost-calculation.md](./cost-calculation.md) | 成本计算（DDU/DDP） |
| [design/shipment-route-status-design.md](./design/shipment-route-status-design.md) | DPS 轨迹明细状态（route_status） |
| [design/dps-update-amz-design.md](./design/dps-update-amz-design.md) | 补货件号保存后推送亚马逊 |
| [design/shipment-groups-design.md](./design/shipment-groups-design.md) | 运单分组与组提醒设计 |
| [design/quote-followup-management-design.md](./design/quote-followup-management-design.md) | 报价跟进管理设计 |
| [design/payment-reminder-list-design.md](./design/payment-reminder-list-design.md) | 催款列表设计 |
| [design/logistics-workbench-home-redesign.md](./design/logistics-workbench-home-redesign.md) | 物流工作台首页改版（阶段一～三已落地） |
| [design/tools/tools-center-design.md](./design/tools/tools-center-design.md) | 工具中心主设计 |
| [design/tools/image-link-zip-design.md](./design/tools/image-link-zip-design.md) | 标签图片打包工具设计 |
| [MIGRATION.md](./MIGRATION.md) | Legacy → v2 迁移指南 |
| [changelog-policy.md](./changelog-policy.md) | 更新记录的范围、写法、敏感信息限制与归档规则 |
| [changelog/2026.md](./changelog/2026.md) | 2026 年 7 月及以前的更新归档 |
| [changelog/2025.md](./changelog/2025.md) | 2025 年更新归档 |

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

仅记录已完成的用户可感知变化及重要升级事项；同日同功能合并，不记录开发流水账或商业价格。主文件保留最近三个自然月，较早内容按年归档。具体规则与格式示例见 [changelog-policy.md](./changelog-policy.md)。

```markdown
## YYYY-MM-DD

### 新增

- 用户可感知的新增能力。

### 升级说明

- 必要的迁移、配置或依赖要求。
```

### 4. 自动更新规则

| 事件 | 必做 |
|------|------|
| 新增功能 | 更新受影响的模块、入口和详细文档；用户可感知时记录 CHANGELOG |
| 修改功能 | 更新受影响的业务流程；使用行为变化时记录 CHANGELOG |
| 修改数据库 | 更新数据库与表结构说明；必要迁移写入 CHANGELOG 升级说明 |
| 新增 API | 更新 API 文档、受影响模块和示例；使用或兼容性变化时记录 CHANGELOG |
| 内部重构、测试、细碎样式 | 检查相关文档；无使用或升级影响时不单列 CHANGELOG |

### 质量要求

- Markdown，含目录与示例
- 与代码保持一致，禁止过期内容
- 发现文档与代码不一致时，**优先修正文档**

## 变更记录

近期记录见 [../CHANGELOG.md](../CHANGELOG.md)；历史归档见 [2026 年](./changelog/2026.md)、[2025 年](./changelog/2025.md)。
