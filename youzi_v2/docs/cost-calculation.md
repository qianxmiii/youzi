# 成本计算

路由：`/cost`（纯前端，无后端 API）

业务分析文档：[costCalTab-analysis.md](../../docs/costCalTab-analysis.md)（仓库根目录）

## 功能

1. **货物识别**：从自然语言解析箱数、重量、体积、尺寸，同步到 DDU 与全部 DDP 行。
2. **自税 DDU**：按方表价、货值、税率（+20% 基础关税）、派送费；支持按方包税。
3. **包税 DDP**：多行试算，按 kg 表价、材积重计费；支持新增/复制/删除行。

## 汇率（与 Legacy 一致）

| 用途 | 常量 | 值 |
|------|------|-----|
| DDU 税金、USD 派送费 | `COST_EXCHANGE_RATE` | 7.1 |
| DDP USD 派送费折算 | `EXCHANGE_RATE` | 6.8 |

## 代码位置

| 路径 | 说明 |
|------|------|
| `frontend/src/views/cost/CostCalculationView.vue` | 页面 |
| `frontend/src/domain/costCalculation/` | 计算与识别逻辑 |
| `frontend/src/constants/costCalculation.ts` | 产品、kg 表价、重量比 |
| `scripts/verify_cost_calculation.ts` | 与文档第 5 节对齐的校验脚本 |

## 本地校验

```bash
cd youzi_v2/frontend
npx tsx ../scripts/verify_cost_calculation.ts
```

## 与 Legacy 对齐说明

- 清空「报价识别」会同步将 DDU/DDP 的箱数、实重、体积置 0
- DDU 表格展示「派送费(RMB)」列（Legacy 为隐藏列，列序：头程费 → 派送费 RMB → 税金）
