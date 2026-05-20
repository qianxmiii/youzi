"""
业务码表：渠道、国家、地址、承运商、港口、运单状态。
时间列统一 YYYY-MM-DD HH:mm:ss。
"""

from __future__ import annotations

import sqlite3
from typing import Iterable

from .datetime_util import now_str

# (table_name, optional extra columns in CREATE)
_CODE_TABLE_DEFS: list[tuple[str, str]] = [
    ("channel_codes", ""),
    ("country_codes", ""),
    ("address_codes", ""),
    ("carrier_codes", ""),
    (
        "port_codes",
        "port_type TEXT NOT NULL DEFAULT 'both',",
    ),
    ("shipment_status_codes", ""),
    ("shipment_exception_codes", ""),
]

_STATUS_SEEDS: list[tuple[str, str, str, int]] = [
    ("IN_TRANSIT", "转运中", "In transit", 10),
    ("DELIVERED", "已签收", "Delivered", 20),
    ("INSPECTION", "查验", "Inspection", 30),
    ("UNKNOWN", "未知", "Unknown", 99),
]

_EXCEPTION_SEEDS: list[tuple[str, str, str, int]] = [
    ("INSPECTION", "查验中", "Inspection", 10),
    ("LOST", "掉件", "Lost", 20),
    ("HOLD", "暂扣", "Hold", 30),
    ("DAMAGED", "破损", "Damaged", 40),
]


def _create_code_table_sql(table: str, extra_cols: str = "") -> str:
    extra_block = f"\n    {extra_cols}" if extra_cols else ""
    return f"""
CREATE TABLE IF NOT EXISTS {table} (
    code TEXT PRIMARY KEY,
    name_zh TEXT NOT NULL DEFAULT '',
    name_en TEXT NOT NULL DEFAULT '',{extra_block}
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    for table, extra in _CODE_TABLE_DEFS:
        conn.execute(_create_code_table_sql(table, extra))


def seed_if_empty(conn: sqlite3.Connection) -> None:
    _seed_status_codes(conn)
    _seed_exception_codes(conn)


def _seed_status_codes(conn: sqlite3.Connection) -> None:
    table = "shipment_status_codes"
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    if row and row["c"] and row["c"] > 0:
        return
    now = now_str()
    conn.executemany(
        f"""
        INSERT INTO {table} (
            code, name_zh, name_en, sort_order, is_active, created_time, updated_time
        ) VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        [(code, zh, en, order, now, now) for code, zh, en, order in _STATUS_SEEDS],
    )


def _seed_exception_codes(conn: sqlite3.Connection) -> None:
    table = "shipment_exception_codes"
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    if row and row["c"] and row["c"] > 0:
        return
    now = now_str()
    conn.executemany(
        f"""
        INSERT INTO {table} (
            code, name_zh, name_en, sort_order, is_active, created_time, updated_time
        ) VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        [(code, zh, en, order, now, now) for code, zh, en, order in _EXCEPTION_SEEDS],
    )


def list_code_tables() -> Iterable[str]:
    return (name for name, _ in _CODE_TABLE_DEFS)
