# 数据层（db）

## 模块名称

Youzi v2 数据层 — SQLite 仓储

## 功能说明

管理 SQLite 连接、表结构（`ensure_schema`）、种子数据及 Repository 查询/写入。所有业务表在应用启动时自动初始化。

## 主要文件

| 路径 | 作用 |
|------|------|
| `connection.py` | 单例 Database、WAL、bootstrap |
| `*_table.py` | 建表 SQL、索引、轻量迁移 |
| `*_repository.py` | 业务查询与 CRUD |
| `shipment_groups_repository.py` | 运单分组 CRUD |
| `datetime_util.py` | 时间字符串工具 |
| `code_tables.py` | 通用码表 |
| `tracking_freshness.py` | 轨迹新鲜度计算 |

## 数据结构

数据库文件默认 `youzi_v2/data/youzi.db`。

核心表：

- `shipments` — 运单
- `shipment_groups` / `shipment_group_members` — 运单分组（见 `shipment_groups_table.py`）
- `vessel_voyages` / `voyage_port_calls` — 船期
- `internal_tracking_logs` / `carrier_tracking_logs` — 轨迹
- `customers`、`channels` — 主数据
- `quote_opportunities` / `quote_versions` / `quote_followups` — 报价跟进
- `shipment_payment_followups` — 催款跟进（列表实时计算；见 `shipment_payment_followups_repository.py`）
- `addresses`、`addresses_warehouse` — 地址簿

完整表说明见 [docs/database.md](../docs/database.md)。

## 使用示例

```python
from pathlib import Path
from youzi_v2.db.connection import get_database
from youzi_v2.db.shipments_repository import list_shipments

db = get_database(Path("youzi_v2/data/youzi.db"))
rows, total = list_shipments(db.conn, page=1, page_size=20)
```

## 注意事项

- 时间列统一 TEXT `YYYY-MM-DD HH:mm:ss`
- 多数外键为逻辑关联，便于 Excel 导入
- 修改表结构：更新 `*_table.py` 的 `ensure_schema` + [docs/database.md](../docs/database.md) + CHANGELOG

## 相关文档

- [docs/database.md](../docs/database.md)
- [docs/modules/shipment/README.md](../docs/modules/shipment/README.md)
