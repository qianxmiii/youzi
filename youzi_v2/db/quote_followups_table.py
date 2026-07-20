"""报价跟进记录表。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "quote_followups"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    quote_version_id TEXT NOT NULL DEFAULT '',
    followup_time TEXT NOT NULL,
    followup_type TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    next_followup_date TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_quote_id "
    f"ON {TABLE_NAME}(quote_id, followup_time DESC)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_followup_time "
    f"ON {TABLE_NAME}(followup_time DESC)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for sql in _INDEXES:
        conn.execute(sql)
