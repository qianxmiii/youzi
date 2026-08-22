# 箱单转产品导入

> **落地状态（2026-08-13）**：已接入工具中心 `/tools/product-import`；API `POST/GET /api/v1/tools/product-import*`。转换逻辑仍用 `tools/product_import/generate_product_import.py`。

## 目标

上传客户箱单发票，按产品导入模板字段映射，生成可导入系统的 `.xls`。

## 流程

1. 选择箱单（`.xls` / `.xlsx`）
2. `POST /api/v1/tools/product-import`（form 字段 `invoice`）
3. `GET /api/v1/tools/product-import/download/{id}` 下载结果

## 配置

| 路径 | 说明 |
| --- | --- |
| `tools/product_import/field_mapping.json` | 箱单列 → 模板列、计算字段、默认值 |
| `tools/product_import/samples/*.xls` | 产品导入空白模板 |

## 说明

- 件数支持 `24CTNS` 等写法
- 表头支持换行附加说明（如 `申报总数量（pcs）`）
- Legacy 页面 `/tools/product-import`（Jinja）与旧接口 `/api/product-import` 仍可用，内部已复用同一转换服务
