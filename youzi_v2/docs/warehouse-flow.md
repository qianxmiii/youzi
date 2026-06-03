# 仓库地址簿业务流程

## 目录

- [概述](#概述)
- [与派送地址簿的区别](#与派送地址簿的区别)
- [数据字段](#数据字段)
- [CRUD 流程](#crud-流程)
- [Excel 导入导出](#excel-导入导出)
- [在运单中的使用](#在运单中的使用)
- [注意事项](#注意事项)

## 概述

仓库地址簿管理**起运仓 / 海外仓**等仓库级地址，供运单填写 `origin_warehouse_code` 及后续扩展使用。前端入口：`/addresses` 页中的仓库地址 Tab（`AddressesView.vue`）。

数据表：`addresses_warehouse`（`db/addresses_warehouse_table.py`）。

## 与派送地址簿的区别

| 项目 | 仓库地址 | 派送地址 |
|------|----------|----------|
| API 前缀 | `/api/addresses-warehouse` | `/api/addresses` |
| 数据表 | addresses_warehouse | addresses |
| 典型用途 | 起运仓、FBA 仓代码 | 收件人派送地址 |
| Excel 模板 | 有专用模板与列配置 | 无批量模板（以当前实现为准） |

## 数据字段

主要字段（详见 `db/addresses_warehouse_table.py`）：

- 仓库编码、仓库名称
- 国家/地区
- 联系人、电话
- 详细地址、邮编
- 备注

列映射配置：`youzi_v2/config/address_excel_columns.json`。

## CRUD 流程

```text
列表查询 → 筛选(filter-options) → 新增/编辑表单 → 保存
                                    ↓
                              删除（单条）
```

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/addresses-warehouse` | 列表 |
| GET | `/api/addresses-warehouse/filter-options` | 筛选项 |
| POST | `/api/addresses-warehouse` | 新建 |
| PUT | `/api/addresses-warehouse/{item_id}` | 更新 |
| DELETE | `/api/addresses-warehouse/{item_id}` | 删除 |

## Excel 导入导出

**下载模板**

```bash
curl -O "http://127.0.0.1:3001/api/addresses-warehouse/template"
```

**导入**

```bash
curl -X POST "http://127.0.0.1:3001/api/addresses-warehouse/import" \
  -F "file=@仓库地址.xlsx"
```

**导出**

```bash
curl -O "http://127.0.0.1:3001/api/addresses-warehouse/export"
```

解析逻辑：`services/address_excel.py`。

## 在运单中的使用

运单表 `shipments.origin_warehouse_code` 存储起运仓编码，与仓库地址簿编码对应（逻辑关联，非强制 FK）。运单表单中可选择或手工输入仓库编码。

## 注意事项

- 启动时 `addresses_warehouse_table.seed_if_empty` 可能写入种子数据
- 导入前请使用最新模板，表头必须与 `address_excel_columns.json` 一致
- 仓库编码建议在团队内统一命名规则，避免运单关联失败

## 相关文档

- [database.md](./database.md)
- [api.md](./api.md)
- [db/README.md](../db/README.md)
