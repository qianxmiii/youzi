"""渠道运输时效规则表。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "channel_sla_rules"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    channel_code TEXT NOT NULL,
    carrier_code TEXT NOT NULL DEFAULT '',
    start_field TEXT NOT NULL DEFAULT 'ATD',
    estimated_days INTEGER NOT NULL,
    warning_days INTEGER NOT NULL DEFAULT 3,
    severe_overdue_days INTEGER NOT NULL DEFAULT 7,
    enabled INTEGER NOT NULL DEFAULT 1,
    note TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    UNIQUE(channel_code, carrier_code, start_field)
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_channel "
    f"ON {TABLE_NAME}(channel_code, enabled)",
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
