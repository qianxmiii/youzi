"""报价版本表。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "quote_versions"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    version_no INTEGER NOT NULL,
    version_time TEXT NOT NULL,
    change_reason TEXT NOT NULL DEFAULT '',
    product_name TEXT NOT NULL DEFAULT '',
    address_text TEXT NOT NULL DEFAULT '',
    ctns INTEGER,
    weight_kg REAL,
    volume_cbm REAL,
    quoted_amount REAL,
    quoted_currency TEXT NOT NULL DEFAULT '',
    profit_amount REAL,
    profit_currency TEXT NOT NULL DEFAULT '',
    profit_rate REAL,
    note TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    UNIQUE(quote_id, version_no)
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_quote_id "
    f"ON {TABLE_NAME}(quote_id, version_no DESC)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for sql in _INDEXES:
        conn.execute(sql)
