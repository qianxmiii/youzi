# 业务服务（services）

## 模块名称

Youzi v2 业务服务层

## 功能说明

封装跨 Repository 的业务逻辑：轨迹同步、Excel 导入导出、承运商对接、船期抓取、海运预警、企业微信智能机器人等。由 `app.py` 路由层调用。

**企业微信**：配置、@ 查运单、主动推送与排障见 [docs/wecom-aibot.md](../docs/wecom-aibot.md)。

## 主要文件

| 文件 | 作用 |
|------|------|
| `tracking_sync.py` | 轨迹同步编排 |
| `tracking_sync_scheduler.py` | 定时任务调度（含订阅 ETA 到港每日提醒） |
| `carrier_tracking_sync.py` | 承运商轨迹拉取（支持 vendor `fallbackVendor` 链） |
| `carrier_vendors.py` | 读取 config.json 承运商配置 |
| `wecom_webhook.py` | 企业微信通知（Webhook 或智能机器人 bot_id+secret） |
| `wecom_aibot_ws.py` | 智能机器人 WebSocket 认证与 `aibot_send_msg` |
| `wecom_aibot_runtime.py` | 长连接守护、心跳、chat_id 日志 |
| `wecom_aibot_log.py` | 长连接运行日志文件 |
| `wecom_aibot_shipment_query.py` | @ 消息解析运单号并查库回复 |
| `shipment_copy_format.py` | 运单明细与转单号复制文案（与前端 `shipmentCopyFormat.ts` 对齐，企微「明细」「转单号」回复复用） |
| `wecom_aibot_shipment_refresh.py` | 查单前刷新明细状态与内外部轨迹 |
| `wecom_subscription_push.py` | 运单订阅更新（轨迹/ETA 提醒）同步推企微 |
| `shipment_query_config.py` | DPS 运单查询、`dps_authorization` 解析；`queryByPerson` / `_pickup` / `_warehoused` / `queryByOrder` 自动翻页 |
| `dps_update_amz.py` | 补货件号保存后推送亚马逊（`config.dps_update_amz`，同一票 60 秒冷却） |
| `amz_port_resolve.py` | 按码表 `amz_update_port_rules` 解析起运港、目的港 |
| `dps_data_download.py` | DPS 货箱重量尺寸下载（`config.dps_data_download`，参数 `ids`） |
| `shipment_dps_cargo_download.py` | 勾选运单批量下载货箱（单票 `{单号}_data.ext`；多票 `{N}票数据_{时间}.zip`） |
| `dps_mark_download.py` | DPS 唛头（单票 / 批量） |
| `shipment_dps_mark_download.py` | 勾选运单下载唛头 |
| `mark_rename.py` | 唛头重命名：字段顺序 + 分隔符拼文件名 |
| `shipment_dps_mark_rename_download.py` | 逐票下载唛头并重命名；可按字段分文件夹后打 zip |
| `mark_pdf_split.py` | 唛头 PDF 按件数拆分命名 |
| `shipment_dps_mark_split_download.py` | 单票唛头拆分 zip 下载 |
| `mark_self_pdf.py` | 自生成唛头 PDF（102mm×102mm，Code128=运单号+箱序） |
| `shipment_mark_self_download.py` | 勾选运单批量自生成唛头 |
| `dps_export_job.py` | DPS 导出异步任务与进度 |
| `dps_packinglist_download.py` | DPS 箱单发票 |
| `shipment_dps_packinglist_download.py` | 勾选运单下载箱单发票 |
| `dps_warehouseform_download.py` | DPS 排仓单 |
| `shipment_dps_warehouseform_download.py` | 勾选运单下载排仓单（超 50 分批） |
| `dps_receive_warehouse.py` | 收货仓名称 → `dps_warehouse` 键（SHENZHEN/YIWU） |
| `dps_warehouse_entry_download.py` | DPS 进仓单请求 |
| `warehouse_entry_template.py` | 进仓单 xlsx 模板占位符填充 |
| `warehouse_entry_xlsx_to_pdf.py` | 进仓单 xlsx → PDF（Excel COM / LibreOffice） |
| `warehouse_entry_pdf.py` | 进仓单 PDF 编排（模板 xlsx + 转换） |
| `shipment_dps_warehouse_entry_download.py` | 勾选运单进仓单 xlsx/PDF（`{N}票进仓单_{日期}`） |
| `shipment_dps_sync.py` | DPS 运单同步至本地表（计划任务默认关；港前可按已下单/提货中/已入仓全部按运单号更新，也可「同步今天」拉提货中与已入仓；在途「同步今天」用 transitTimeDateRange） |
| `dps_waybill_route_info.py` | DPS 明细状态轨迹查询（URL 仅读 config `dps_route_status_query`） |
| `dps_order_product.py` | DPS 运单产品（`config.dps_getOrderProduct`，参数 `commerceWaybillId`；只取中文品名、英文品名、箱数；可批量核对箱数与运单件数） |
| `shipment_dps_route_status_sync.py` | 轻量回写 `route_status`、阶段 `route_*_time`；301/306 且 ATD/ATA 空时回写开船/到港时间 |
| `shipment_route_status_exception.py` | 206/402 清关异常自动开/关 |
| `shipment_dps_mapper.py` | DPS API rows → shipments 字段映射（含计费重，以及应收/应付/利润人民币与利润率） |
| `shipment_dps_sync_fields.py` | 同步字段白名单（`config/shipment_dps_sync_fields.json`） |
| `logistics_tracking.py` | 物流轨迹解析 |
| `shipment_excel.py` | 运单 Excel 导入导出 |
| `payment_reminder_rules.py` | 催款结算/应催日期计算 |
| `payment_reminder_excel.py` | 催款列表 Excel 导出 |
| `customer_excel.py` | 客户管理 Excel 导出 |
| `vessel_schedule_excel.py` | 船期 Excel |
| `address_excel.py` | 仓库地址 Excel |
| `customer_address_excel.py` | 客户地址簿 Excel 模板、导入与导出 |
| `vessel_schedule_sync.py` | 外部船期同步 |
| `maritime_alerts.py` | 海运预警聚合 |
| `workbench_overview.py` | 工作台首页聚合（今日重点 / 待办 / 近期到港 / 明细状态漏斗 / 运输概览） |
| `image_link_zip.py` | Excel 图片链接下载打包 |
| `shipment_file_rename.py` | 运单文件重命名：解析 Excel 映射 |
| `product_import_convert.py` | 箱单 → 产品导入模版（调用 tools/product_import 脚本） |
| `maritime_schedule/` | 船期数据源（如 COSCO eLines） |
| `port_code_resolve.py` | 港口码解析 |
| `scheduled_sync_settings.py` | 计划任务配置 |
| `order_flow_client.py` / `order_flow_sync.py` | 订单流转拉取与 5 分钟轮询（默认关闭） |
| `quote_paste.py` | 报价跟进：把粘贴原文解析成仓点、渠道行、提货费和合计 |

## 业务流程

**轨迹定时同步**

```text
scheduler 触发 → 筛选 IN_TRANSIT 运单 → internal_sync + carrier_sync
              → 写日志表 → 更新 shipments 最新轨迹字段
```

**船期 Excel 导入**

```text
上传 xlsx → vessel_schedule_excel 解析 → upsert vessel_voyages + voyage_port_calls
```

## 注意事项

- 承运商 API 密钥仅通过 `carrier_vendors.py` 读 `config/config.json`
- 同步日志：`services/sync_log.py` → `youzi_v2/logs/`
- 新增承运商：实现 vendor adapter + 配置 `vendors` 数组 + 文档

## 相关文档

- [docs/shipment-flow.md](../docs/shipment-flow.md)
- [docs/deployment.md](../docs/deployment.md)

### DW 计算

`delivery_window.py` 按 ATD（缺省时 ETD）及渠道全程范围，同时参考ATA（无ATA时ETA）与到港后送仓区间，起止日期分别取较晚值；人工窗口优先，AMZ 自动使用周窗口，其他地址不推断为亚马逊。配置计算不读取历史统计，也不修改原预计送仓字段或预警期限。详见 [业务说明](../docs/delivery-window.md)。

`delivery_window_history.py` 独立只读加载历史参考，以目的仓签收为终点，按可识别运输批次合并后计算P50/P90；区分实际含异常、正常与近30天样本。仅在各必要段达到5个有效批次时生成参考窗口，不自动改写配置或人工值。沿用统计模块的分位数算法，但不复用其排除长异常后的样本，以保留实际履约表现。
