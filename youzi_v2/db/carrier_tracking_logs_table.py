"""承运商轨迹表 carrier_tracking_logs。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "carrier_tracking_logs"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    shipment_no TEXT NOT NULL,
    vendor_name TEXT NOT NULL DEFAULT '',
    carrier_code TEXT NOT NULL DEFAULT '',
    tracking_time TEXT NOT NULL,
    tracking_desc TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_no ON {TABLE_NAME}(shipment_no)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_vendor ON {TABLE_NAME}(vendor_name)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_time "
    f"ON {TABLE_NAME}(shipment_no, tracking_time DESC)",
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_dedup "
    f"ON {TABLE_NAME}(shipment_no, vendor_name, tracking_time, tracking_desc)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for stmt in _INDEXES:
        conn.execute(stmt)
