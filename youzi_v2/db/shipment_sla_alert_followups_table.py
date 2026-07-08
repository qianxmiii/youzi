"""运输时效预警跟进记录表。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "shipment_sla_alert_followups"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL,
    followed_time TEXT NOT NULL,
    created_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_alert "
    f"ON {TABLE_NAME}(alert_id, followed_time DESC)",
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
