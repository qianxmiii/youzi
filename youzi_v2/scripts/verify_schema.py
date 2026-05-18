"""一次性校验：启动 DB 并打印 shipments / 码表结构。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from youzi_v2.db.connection import get_database

db = get_database(Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db")
c = db.conn
tables = [r[0] for r in c.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()]
print("tables:", tables)
print("status codes:", list(c.execute(
    "SELECT code, name_zh FROM shipment_status_codes ORDER BY sort_order"
).fetchall()))
cols = [r[1] for r in c.execute("PRAGMA table_info(shipments)").fetchall()]
print("shipments columns:", cols)
if "sys_dict" in tables:
    dict_cols = [r[1] for r in c.execute("PRAGMA table_info(sys_dict)").fetchall()]
    print("sys_dict columns:", dict_cols)
