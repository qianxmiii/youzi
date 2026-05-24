"""客户表：从运单 customer 同步，支持 VIP 标识。"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "customers"
LEGACY_VIP_TABLE = "vip_customers"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    track_query_lang TEXT NOT NULL DEFAULT 'zh',
    is_vip INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    shipment_count INTEGER NOT NULL DEFAULT 0,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_customer_name "
    f"ON {TABLE_NAME}(customer_name)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_is_vip ON {TABLE_NAME}(is_vip)",
]


def _migrate_legacy_vip_table(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (LEGACY_VIP_TABLE,),
    ).fetchone()
    if not row:
        return
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
    if "name_zh" in cols:
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {TABLE_NAME}
                (id, customer_name, name_zh, name_en, track_query_lang,
                 is_vip, note, shipment_count, created_time, updated_time)
            SELECT id, customer_name, '', '', 'zh', 1, note, 0, created_time, updated_time
            FROM {LEGACY_VIP_TABLE}
            """
        )
    else:
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {TABLE_NAME}
                (id, customer_name, track_query_lang,
                 is_vip, note, shipment_count, created_time, updated_time)
            SELECT id, customer_name, 'zh', 1, note, 0, created_time, updated_time
            FROM {LEGACY_VIP_TABLE}
            """
        )


def _migrate_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
    if "track_query_lang" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN track_query_lang TEXT NOT NULL DEFAULT 'zh'"
        )


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for sql in _INDEXES:
        conn.execute(sql)
    _migrate_legacy_vip_table(conn)
    _migrate_columns(conn)
