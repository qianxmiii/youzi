"""运输时效预警表。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "shipment_sla_alerts"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL,
    alert_type TEXT NOT NULL DEFAULT 'DELIVERY_TIME',
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning',
    rule_id TEXT NOT NULL DEFAULT '',
    rule_scope TEXT NOT NULL DEFAULT 'channel',
    channel_code TEXT NOT NULL DEFAULT '',
    carrier_code TEXT NOT NULL DEFAULT '',
    start_field TEXT NOT NULL DEFAULT '',
    start_time TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL,
    warning_date TEXT NOT NULL DEFAULT '',
    converted_exception_code TEXT NOT NULL DEFAULT '',
    converted_event_id TEXT NOT NULL DEFAULT '',
    acknowledged_time TEXT NOT NULL DEFAULT '',
    resolved_time TEXT NOT NULL DEFAULT '',
    ignored_time TEXT NOT NULL DEFAULT '',
    owner TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    event_key TEXT NOT NULL UNIQUE,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment "
    f"ON {TABLE_NAME}(shipment_id, status)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_status_risk "
    f"ON {TABLE_NAME}(status, risk_level, due_date)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_no "
    f"ON {TABLE_NAME}(shipment_no)",
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
