# 标签图片打包设计

> 归属：[tools-center-design.md](./tools-center-design.md)
> 路由：`/tools/image-link-zip`
> 入口：工具中心卡片「标签图片打包」

## 1. 业务目标与非目标

**目标**

- 从 Excel 指定列读取图片 URL，批量下载并打成 ZIP，便于线下打印/归档标签图。

**非目标**

- 不修改运单、客户等业务库数据。
- 不在工具页内编辑 Excel 内容。
- 首期不做权限细分（随工具中心权限模型一并扩展）。

## 2. 用户流程

1. 从工具中心进入本页。
2. 选择 `.xls` / `.xlsx`，确认链接列（默认 `P`）。
3. 点击「下载并打包」→ 创建后台任务，页面轮询进度。
4. 完成后自动下载 ZIP；展示成功/失败统计。

## 3. 输入 / 输出

| 项 | 说明 |
| --- | --- |
| 输入文件 | `.xls` / `.xlsx` / `.xlsm`，≤ 30MB |
| 列 | 字母列，默认 `P`；跳过表头与空单元格 |
| 链接 | 仅 `http://` / `https://` |
| 上限 | 去重后最多 500 条；单图 ≤ 20MB |
| 输出 | `标签图片_YYYYMMDD_HHMMSS.zip`；响应头含 total/downloaded/failed |

## 4. API 与任务模型

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/tools/image-link-zip/jobs` | 上传 Excel，创建任务，返回 `jobId` |
| GET | `/api/v1/tools/image-link-zip/jobs/{jobId}` | 进度：`status` / `done` / `total` / `failed` |
| GET | `/api/v1/tools/image-link-zip/jobs/{jobId}/download` | 完成后下载 ZIP |

- 实现：`services/image_link_zip.py` + `routers/tools.py`
- 任务内存保存，约 1 小时过期清理；进程重启后任务丢失（可接受）。
- 并发下载（默认 16 workers）。

## 5. 异常处理

- 无有效链接、列越界、格式错误 → 400，文案说明如何修正。
- 部分图片失败 → 仍生成 ZIP（至少 1 张成功），统计失败数。
- 全部失败 → 任务 `failed`，不提供下载。

## 6. 验收与测试

- [ ] 工具中心卡片可进入本页，侧栏无单独菜单项。
- [ ] 有效 Excel + P 列链接可完成打包并下载。
- [ ] 进度条随 `done/total` 更新；执行中禁止重复提交。
- [ ] 空链接 / 非法列 / 非 Excel 有明确错误提示。
- [ ] 单测覆盖 URL 提取与 ZIP 生成（`tests/test_image_link_zip.py`）。
