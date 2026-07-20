# 请求/响应模型（schemas）

## 模块名称

Pydantic Schemas

## 功能说明

定义 FastAPI 路由的请求体、响应体与校验规则，与前端 `src/types/` 保持语义一致。

## 主要文件

| 文件 | 说明 |
|------|------|
| `shipments.py` | 运单 CRUD、批量、同步 |
| `vessel_schedules.py` | 航次、挂靠、导入 |
| `maritime_alerts.py` | 海运预警 |
| `workbench.py` | 工作台首页聚合 |
| `tracking.py` | 轨迹日志 |
| `shipment_exceptions.py` | 异常开/关 |
| `customers.py` | 客户 |
| `channels.py` | 渠道 |
| `code_tables.py` | 码表 |
| `tracking_freshness.py` | 轨迹新鲜度统计 |

## 使用示例

```python
from youzi_v2.schemas.shipments import ShipmentCreate, ShipmentOut

@app.post("/api/v1/shipments", response_model=ShipmentOut)
def create_shipment(body: ShipmentCreate):
    ...
```

## 注意事项

- 字段变更需同步：前端 types、`docs/api.md`、模块 README
- 可选字段使用 `Optional` 或默认值，与 DB NULL 语义对齐

## 相关文档

- [docs/api.md](../docs/api.md)
