"""轨迹同步任务记录 tracking_sync_jobs。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "tracking_sync_jobs"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    status TEXT NOT NULL,
    total_shipments INTEGER NOT NULL DEFAULT 0,
    updated_shipments INTEGER NOT NULL DEFAULT 0,
    new_log_count INTEGER NOT NULL DEFAULT 0,
    skipped INTEGER NOT NULL DEFAULT 0,
    empty_count INTEGER NOT NULL DEFAULT 0,
    not_found INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    errors_json TEXT NOT NULL DEFAULT '[]',
    summary_json TEXT NOT NULL DEFAULT '{{}}',
    started_time TEXT NOT NULL,
    finished_time TEXT
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_source_time "
    f"ON {TABLE_NAME}(source, started_time DESC)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for stmt in _INDEXES:
        conn.execute(stmt)
