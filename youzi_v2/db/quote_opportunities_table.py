"""报价机会主表。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "quote_opportunities"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    quote_no TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL DEFAULT '',
    customer_name TEXT NOT NULL DEFAULT '',
    is_new_customer INTEGER NOT NULL DEFAULT 0,
    customer_inquiry_no TEXT NOT NULL DEFAULT '',
    quote_date TEXT NOT NULL,
    deadline_date TEXT NOT NULL DEFAULT '',
    followup_interval_days INTEGER NOT NULL DEFAULT 1,
    next_followup_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'QUOTED',
    owner TEXT NOT NULL DEFAULT '',
    product_name TEXT NOT NULL DEFAULT '',
    address_text TEXT NOT NULL DEFAULT '',
    ctns INTEGER,
    weight_kg REAL,
    volume_cbm REAL,
    current_quote_version_id TEXT NOT NULL DEFAULT '',
    current_quoted_amount REAL,
    current_quoted_currency TEXT NOT NULL DEFAULT '',
    current_profit_amount REAL,
    current_profit_currency TEXT NOT NULL DEFAULT '',
    current_profit_rate REAL,
    lost_reason TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    converted_shipment_id TEXT NOT NULL DEFAULT '',
    converted_shipment_no TEXT NOT NULL DEFAULT '',
    converted_time TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_customer "
    f"ON {TABLE_NAME}(customer_name)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_status "
    f"ON {TABLE_NAME}(status)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_next_followup "
    f"ON {TABLE_NAME}(next_followup_date)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_deadline "
    f"ON {TABLE_NAME}(deadline_date)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_owner "
    f"ON {TABLE_NAME}(owner)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for sql in _INDEXES:
        conn.execute(sql)
