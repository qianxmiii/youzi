"""运单轨迹时间候选表 shipment_tracking_time_candidates。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "shipment_tracking_time_candidates"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    candidate_value TEXT NOT NULL,
    compare_value TEXT NOT NULL DEFAULT '',
    recommended_source TEXT NOT NULL DEFAULT '',
    compare_source TEXT NOT NULL DEFAULT '',
    source_track_id TEXT NOT NULL DEFAULT '',
    source_track_time TEXT NOT NULL DEFAULT '',
    source_track_desc TEXT NOT NULL DEFAULT '',
    compare_source_track_id TEXT NOT NULL DEFAULT '',
    compare_source_track_time TEXT NOT NULL DEFAULT '',
    compare_source_track_desc TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT 'high',
    review_status TEXT NOT NULL DEFAULT 'auto_confirmed',
    review_reason TEXT NOT NULL DEFAULT '',
    applied INTEGER NOT NULL DEFAULT 0,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    UNIQUE(shipment_id, field_name)
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment "
    f"ON {TABLE_NAME}(shipment_id)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_review "
    f"ON {TABLE_NAME}(review_status)",
]

_MIGRATION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("compare_value", "TEXT NOT NULL DEFAULT ''"),
    ("recommended_source", "TEXT NOT NULL DEFAULT ''"),
    ("compare_source", "TEXT NOT NULL DEFAULT ''"),
    ("compare_source_track_id", "TEXT NOT NULL DEFAULT ''"),
    ("compare_source_track_time", "TEXT NOT NULL DEFAULT ''"),
    ("compare_source_track_desc", "TEXT NOT NULL DEFAULT ''"),
)


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE_NAME,),
    )
    if cur.fetchone() is None:
        conn.execute(_CREATE_SQL)
    for stmt in _INDEXES:
        conn.execute(stmt)

    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
    for col_name, col_def in _MIGRATION_COLUMNS:
        if col_name not in cols:
            conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {col_name} {col_def}")
