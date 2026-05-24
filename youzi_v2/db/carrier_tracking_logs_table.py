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
    vendor_event_id TEXT,
    created_time TEXT NOT NULL
)
"""

_DEDUP_INDEX = f"idx_{TABLE_NAME}_dedup"

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_no ON {TABLE_NAME}(shipment_no)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_vendor ON {TABLE_NAME}(vendor_name)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_time "
    f"ON {TABLE_NAME}(shipment_no, tracking_time DESC)",
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_vendor_event_id "
    f"ON {TABLE_NAME}(shipment_no, vendor_name, vendor_event_id) "
    f"WHERE vendor_event_id IS NOT NULL AND TRIM(vendor_event_id) != ''",
]

# 无 vendor_event_id 时按 time+desc 去重；有 event_id 时允许多条同文案（同秒重复节点）
_DEDUP_INDEX_SQL = (
    f"CREATE UNIQUE INDEX IF NOT EXISTS {_DEDUP_INDEX} "
    f"ON {TABLE_NAME}(shipment_no, vendor_name, tracking_time, tracking_desc) "
    f"WHERE vendor_event_id IS NULL OR TRIM(vendor_event_id) = ''"
)


def _migrate_dedup_index(conn: sqlite3.Connection) -> None:
    conn.execute(f"DROP INDEX IF EXISTS {_DEDUP_INDEX}")
    conn.execute(_DEDUP_INDEX_SQL)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    cols = {
        row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()
    }
    if "vendor_event_id" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN vendor_event_id TEXT")
    for stmt in _INDEXES:
        conn.execute(stmt)
    _migrate_dedup_index(conn)
