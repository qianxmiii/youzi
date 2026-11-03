"""客户自己的收货联系地址。与派送地址簿、仓库地址簿分开。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "customer_addresses"

KIND_WAREHOUSE = "WAREHOUSE"
KIND_COMMERCIAL = "COMMERCIAL"
KIND_RESIDENTIAL = "RESIDENTIAL"
ADDRESS_KINDS: frozenset[str] = frozenset(
    {KIND_WAREHOUSE, KIND_COMMERCIAL, KIND_RESIDENTIAL}
)
ADDRESS_KIND_LABELS: dict[str, str] = {
    KIND_WAREHOUSE: "海外仓",
    KIND_COMMERCIAL: "商业",
    KIND_RESIDENTIAL: "住宅",
}

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    consignee_name TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    postcode TEXT NOT NULL DEFAULT '',
    address_kind TEXT NOT NULL,
    is_remote INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = (
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_customer "
    f"ON {TABLE_NAME}(customer_name)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_kind "
    f"ON {TABLE_NAME}(address_kind)",
)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for sql in _INDEXES:
        conn.execute(sql)
