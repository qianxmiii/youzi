"""异常跟进提醒通知表。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "shipment_exception_followup_notifications"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL,
    exception_code TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning',
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    days_open INTEGER NOT NULL DEFAULT 0,
    followup_interval_days INTEGER NOT NULL DEFAULT 3,
    event_key TEXT NOT NULL UNIQUE,
    triggered_at TEXT NOT NULL,
    read_at TEXT NOT NULL DEFAULT '',
    resolved_at TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_no "
    f"ON {TABLE_NAME}(shipment_no)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_triggered "
    f"ON {TABLE_NAME}(triggered_at DESC)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_pending "
    f"ON {TABLE_NAME}(shipment_no, resolved_at)",
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
