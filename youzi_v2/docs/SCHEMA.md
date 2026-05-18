# 数据表说明（youzi_v2）

## 时间格式

所有业务时间字段类型为 `TEXT`，值为 **`YYYY-MM-DD HH:mm:ss`**（例：`2026-05-17 14:30:00`）。

工具函数：`youzi_v2.db.datetime_util.now_str()`

---

## 码表（6 张）

结构相同（`port_codes` 多一列 `port_type`：`origin` | `destination` | `both`）：

| 列 | 说明 |
|----|------|
| `code` | 主键，业务编码 |
| `name_zh` | 中文名 |
| `name_en` | 英文名 |
| `sort_order` | 排序 |
| `is_active` | 1 启用 / 0 停用 |
| `created_time` | 创建时间 |
| `updated_time` | 更新时间 |

| 表名 | 用途 |
|------|------|
| `channel_codes` | 渠道 |
| `country_codes` | 国家 |
| `address_codes` | 地址/仓库代码（部分有码表） |
| `carrier_codes` | 承运商 |
| `port_codes` | 出发/到达港口（共用） |
| `shipment_status_codes` | 运单状态 |

### 初始状态码

| code | name_zh |
|------|---------|
| `IN_TRANSIT` | 转运中 |
| `DELIVERED` | 已签收 |
| `INSPECTION` | 查验 |
| `UNKNOWN` | 未知 |

---

## 运单主表 `shipments`

| 列名 | 说明 | 码表 |
|------|------|------|
| `id` | UUID 主键 | |
| `shipment_no` | 运单号，**唯一** | |
| `customer` | 客户（文本） | |
| `customer_no` | 客户单号 | |
| `channel_code` | 渠道 | `channel_codes` |
| `country_code` | 国家 | `country_codes` |
| `address_type` | 地址类型：`AMZ` / `WFS` / `3PL`，可空 | |
| `address_code` | 地址/仓库代码 | `address_codes` |
| `delivery_address` | 派送地址（Excel 导入） | |
| `ctns` | 件数/箱数（Excel 导入） | |
| `zipcode` | 邮编 | |
| `product_name` | 品名（文本） | |
| `origin_warehouse_code` | 发货仓库 | |
| `supplier_name` | 供应商（文本） | |
| `carrier_code` | 承运商 | `carrier_codes` |
| `customer_shipment_id` | 货件号 | |
| `amazon_ref_id` | 亚马逊预约号 | |
| `vessel_name` | 船名 | |
| `voyage_no` | 航次 | |
| `vessel_voyage` | 船名航次（冗余） | |
| `etd` | 预计离港 | |
| `eta` | 预计到港 | |
| `atd` | 实际离港 | |
| `ata` | 实际到港 | |
| `origin_port_code` | 出发港口 | `port_codes` |
| `destination_port_code` | 到达港口 | `port_codes` |
| `delivered_time` | 签收时间 | |
| `status_code` | 状态 | `shipment_status_codes` |
| `created_time` | 创建时间 | |
| `updated_time` | 更新时间 | |

**索引**：`shipment_no`(UNIQUE)、`customer`、`channel_code`、`country_code`、`carrier_code`、`status_code`、`updated_time`。

---

## 运单轨迹表 `tracking_logs`

一个运单号可有多条轨迹（一对多，通过 `shipment_no` 关联 `shipments.shipment_no`）。

| 列名 | 说明 |
|------|------|
| `id` | UUID 主键 |
| `shipment_no` | 运单号 |
| `tracking_time` | 轨迹时间 `YYYY-MM-DD HH:mm:ss` |
| `tracking_desc` | 轨迹描述 |
| `created_time` | 写入本系统时间 |

**索引**：`shipment_no`；`(shipment_no, tracking_time DESC)` 便于按运单查最新轨迹。

仓储：`youzi_v2/db/tracking_logs_repository.py`（按运单号列表、单条新增、整单替换轨迹）。

---

## 启动时建表

启动 `uvicorn youzi_v2.app:app` 时会自动 `CREATE TABLE` 并写入状态码种子数据。

数据库文件：`youzi_v2/data/youzi_v2.db`

---

## 运单 API（`youzi_v2/app.py`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/shipments` | 列表，`?search=&limit=&offset=` |
| GET | `/api/v1/shipments/{id}` | 单条 |
| POST | `/api/v1/shipments` | 新增（`shipmentNo` 必填） |
| PUT | `/api/v1/shipments/{id}` | 更新（不可改运单号） |
| DELETE | `/api/v1/shipments/{id}` | 删除 |
| POST | `/api/v1/shipments/import` | 上传 Excel，按运单号 upsert |

### Excel 列映射

配置文件：`youzi_v2/config/shipment_excel_columns.json`

| Excel 表头 | 字段 |
|------------|------|
| 运单号 | `shipment_no` |
| 客户订单号 | `customer_no` |
| 用户名 | `customer` |
| 件数 | `ctns` |
| 国家 | `country_code`（如 美国→US） |
| 派送仓库 | `address_code` |
| 派送地址 | `delivery_address` |
| 渠道 | `channel_code` |
| 承运商 | `carrier_code` |
| 交货仓库 | `origin_warehouse_code` |

导入时自动推断 `address_type`：订单号/地址含 FBA→`AMZ`，含 WFS→`WFS`，含 3PL→`3PL`；默认状态 `UNKNOWN`。
