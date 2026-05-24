"""运单追踪号表：主单号 + 子单号（TOPDA subTrackings 等）。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "shipment_tracking_numbers"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    shipment_no TEXT NOT NULL,
    main_tracking_number TEXT NOT NULL,
    tracking_number TEXT NOT NULL,
    is_main INTEGER NOT NULL DEFAULT 0,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_no "
    f"ON {TABLE_NAME}(shipment_no)",
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_tracking "
    f"ON {TABLE_NAME}(shipment_no, tracking_number)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for sql in _INDEXES:
        conn.execute(sql)
