"""运单催款跟进记录表。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "shipment_payment_followups"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL,
    customer TEXT NOT NULL DEFAULT '',
    settlement_method TEXT NOT NULL DEFAULT '',
    reminder_type TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL DEFAULT '',
    followup_time TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_id "
    f"ON {TABLE_NAME}(shipment_id)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_no "
    f"ON {TABLE_NAME}(shipment_no)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_followup_time "
    f"ON {TABLE_NAME}(followup_time DESC)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_customer "
    f"ON {TABLE_NAME}(customer)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for sql in _INDEXES:
        conn.execute(sql)
