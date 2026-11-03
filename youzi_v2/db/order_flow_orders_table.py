"""订单流转快照。只记流转系统自己的运单号，不关联本地运单表。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "order_flow_orders"
LOG_TABLE_NAME = "order_flow_status_logs"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    waybill_no TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL DEFAULT '',
    current_status TEXT NOT NULL DEFAULT '',
    previous_status TEXT NOT NULL DEFAULT '',
    pieces TEXT NOT NULL DEFAULT '',
    weight_kg TEXT NOT NULL DEFAULT '',
    charge_weight_kg TEXT NOT NULL DEFAULT '',
    volume_cbm TEXT NOT NULL DEFAULT '',
    product_name TEXT NOT NULL DEFAULT '',
    warehouse_name TEXT NOT NULL DEFAULT '',
    country_name TEXT NOT NULL DEFAULT '',
    channel_name TEXT NOT NULL DEFAULT '',
    last_operate_time TEXT NOT NULL DEFAULT '',
    previous_operate_time TEXT NOT NULL DEFAULT '',
    mine INTEGER NOT NULL DEFAULT 0,
    ended INTEGER NOT NULL DEFAULT 0,
    status_changed INTEGER NOT NULL DEFAULT 0,
    status_changed_at TEXT NOT NULL DEFAULT '',
    first_seen_time TEXT NOT NULL,
    last_seen_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_LOG_SQL = f"""
CREATE TABLE IF NOT EXISTS {LOG_TABLE_NAME} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    waybill_no TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '',
    operate_time TEXT NOT NULL DEFAULT '',
    recorded_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{LOG_TABLE_NAME}_waybill "
    f"ON {LOG_TABLE_NAME}(waybill_no, id)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_mine "
    f"ON {TABLE_NAME}(mine, ended)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_ended "
    f"ON {TABLE_NAME}(ended, updated_time)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    conn.execute(_LOG_SQL)
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})")}
    if "previous_operate_time" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN previous_operate_time TEXT NOT NULL DEFAULT ''"
        )
    if "status_changed_at" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN status_changed_at TEXT NOT NULL DEFAULT ''"
        )
    if "country_name" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN country_name TEXT NOT NULL DEFAULT ''"
        )
    for sql in _INDEXES:
        conn.execute(sql)
