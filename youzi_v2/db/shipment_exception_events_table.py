"""运单异常事件表：记录每次标记/解除，用于统计持续时间。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "shipment_exception_events"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    shipment_no TEXT NOT NULL,
    exception_code TEXT NOT NULL,
    opened_time TEXT NOT NULL,
    closed_time TEXT,
    note TEXT,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_no "
    f"ON {TABLE_NAME}(shipment_no)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_opened_time "
    f"ON {TABLE_NAME}(opened_time DESC)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_open "
    f"ON {TABLE_NAME}(shipment_no, closed_time)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE_NAME,),
    )
    if cur.fetchone() is None:
        conn.execute(_CREATE_SQL)
        for stmt in _INDEXES:
            conn.execute(stmt)
