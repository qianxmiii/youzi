# 进仓单 Excel 模板

## 文件

| 文件 | 说明 |
|------|------|
| `warehouse_entry_template.xlsx` | 进仓单版式（表头含 **目的国**；明细可用 `{国家}` / 表头「目的国」列，取自运单 `countryCode`） |

重新生成默认模板（会覆盖 xlsx）：

```bash
python youzi_v2/scripts/build_warehouse_entry_template.py
```

## 怎么用

1. 用 Excel/WPS 打开 `warehouse_entry_template.xlsx`，按公司规范改字体、合并、列宽、打印区域。
2. 需要程序填写的格子保留 **`{占位符}`** 写法（见 sheet「占位符说明」）。
3. **「下载 → 进仓单」已接入本模板**：按勾选运单填充占位符并输出 `{N}票进仓单_{YYYYMMDD}.xlsx`（无需 DPS 进仓单接口、无需 waybillId）。
4. **「下载 → 进仓单（PDF）」**：先用本模板生成临时 xlsx，再由本机 Excel 或 LibreOffice 转为 PDF（版式与 xlsx 下载一致）。

可选在 `config/config.json` 指定其它模板路径：

```json
"warehouse_entry_template": "youzi_v2/config/templates/warehouse_entry_template.xlsx"
```

## 明细区约定

- 表头行（序号、运单号…）下一行即为 **首行明细**（可含 `{运单号}`）；模板里多写的序号 2、3… 空行会在生成时 **自动删掉**。
- 勾选运单 **任意票数**：程序在「合计」行上方 **自动插行** 并复制首行样式（不受模板只留 5 行限制）。
- **特殊备注栏**（「特殊备注栏 / 特殊要求」）：固定在合计行下方；明细扩行时整段随之下移，合并版式保留。右侧可写 `{特殊备注}`，由 `config.json` → `dps_warehouse_entry_remarks`（按 `SHENZHEN` / `YIWU`）填充；无占位符则保持模板原文。
- 仅 **明细行区间** 会临时解除合并以便写入，不影响备注栏、收货地址区。

## 相关配置

收货地址文案：`config/config.json` → `dps_warehouse.SHENZHEN` / `YIWU`（勿提交 Git）。
