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

    # DW bounds are independent from alert thresholds; existing rules keep zero padding.
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})")}
    for column in ("dw_early_days", "dw_late_days"):
        if column not in cols:
            conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0")

    if "estimated_days_min" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN estimated_days_min INTEGER")
    conn.execute(f"UPDATE {TABLE_NAME} SET estimated_days_min = estimated_days WHERE estimated_days_min IS NULL")

    for column, default in (("post_arrival_days_min", 7), ("post_arrival_days_max", 15)):
        if column not in cols:
            conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column} INTEGER NOT NULL DEFAULT {default}")
