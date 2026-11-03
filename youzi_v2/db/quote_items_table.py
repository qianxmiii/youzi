"""报价明细：一个版本下的仓点渠道行。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "quote_items"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    quote_version_id TEXT NOT NULL,
    sort_no INTEGER NOT NULL DEFAULT 0,
    address_code TEXT NOT NULL DEFAULT '',
    ctns INTEGER,
    weight_kg REAL,
    volume_cbm REAL,
    trade_term TEXT NOT NULL DEFAULT '',
    channel_name TEXT NOT NULL DEFAULT '',
    unit_price REAL,
    charge_weight_kg REAL,
    quoted_amount REAL,
    quoted_currency TEXT NOT NULL DEFAULT '',
    price_basis TEXT NOT NULL DEFAULT '',
    transit_days_min INTEGER,
    transit_days_max INTEGER,
    note TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_version "
    f"ON {TABLE_NAME}(quote_version_id, sort_no)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})")}
    if "price_basis" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN price_basis TEXT NOT NULL DEFAULT ''"
        )
    for sql in _INDEXES:
        conn.execute(sql)
