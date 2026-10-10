"""
业务码表：渠道、国家、地址、承运商、港口、运单状态。
时间列统一 YYYY-MM-DD HH:mm:ss。
"""

from __future__ import annotations

import sqlite3
from typing import Iterable

from .datetime_util import now_str
from .shipment_route_status import ROUTE_STATUS_SEEDS

# (table_name, optional extra columns in CREATE)
_CODE_TABLE_DEFS: list[tuple[str, str]] = [
    (
        "channel_codes",
        "country TEXT NOT NULL DEFAULT '',\n    category TEXT NOT NULL DEFAULT '',\n    note TEXT NOT NULL DEFAULT '',\n    dps_channel_name TEXT NOT NULL DEFAULT '',",
    ),
    ("country_codes", ""),
    ("address_codes", ""),
    ("carrier_codes", "carrier_id TEXT NOT NULL DEFAULT '',"),
    (
        "port_codes",
        "port_type TEXT NOT NULL DEFAULT 'both',",
    ),
    ("shipment_status_codes", ""),
    ("shipment_exception_codes", ""),
    (
        "shipment_route_status_codes",
        "dps_status TEXT NOT NULL DEFAULT '',",
    ),
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
    ("TRANSIT_TIMEOUT", "运输超时", "Transit timeout", 50),
    ("EXPORT_CUSTOMS_EXCEPTION", "出口海关异常", "Export customs exception", 60),
    ("IMPORT_CUSTOMS_EXCEPTION", "进口清关异常", "Import customs exception", 70),
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


def _migrate_channel_codes(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(channel_codes)").fetchall()}
    for col, ddl in (
        ("country", "ALTER TABLE channel_codes ADD COLUMN country TEXT NOT NULL DEFAULT ''"),
        ("category", "ALTER TABLE channel_codes ADD COLUMN category TEXT NOT NULL DEFAULT ''"),
        ("note", "ALTER TABLE channel_codes ADD COLUMN note TEXT NOT NULL DEFAULT ''"),
        (
            "dps_channel_name",
            "ALTER TABLE channel_codes ADD COLUMN dps_channel_name TEXT NOT NULL DEFAULT ''",
        ),
    ):
        if col not in cols:
            conn.execute(ddl)


def _migrate_carrier_codes(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(carrier_codes)").fetchall()}
    if "carrier_id" not in cols:
        conn.execute(
            "ALTER TABLE carrier_codes ADD COLUMN carrier_id TEXT NOT NULL DEFAULT ''"
        )


def ensure_schema(conn: sqlite3.Connection) -> None:
    for table, extra in _CODE_TABLE_DEFS:
        conn.execute(_create_code_table_sql(table, extra))
    _migrate_channel_codes(conn)
    _migrate_carrier_codes(conn)
    _migrate_route_status_codes(conn)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    _seed_status_codes(conn)
    _seed_exception_codes(conn)
    _sync_exception_codes(conn)
    _sync_route_status_codes(conn)
    _seed_channel_codes(conn)


def _migrate_route_status_codes(conn: sqlite3.Connection) -> None:
    cols = {
        row[1] for row in conn.execute("PRAGMA table_info(shipment_route_status_codes)").fetchall()
    }
    if cols and "dps_status" not in cols:
        conn.execute(
            "ALTER TABLE shipment_route_status_codes "
            "ADD COLUMN dps_status TEXT NOT NULL DEFAULT ''"
        )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_shipment_route_status_dps
        ON shipment_route_status_codes(dps_status)
        WHERE TRIM(dps_status) != ''
        """
    )


def _seed_channel_codes(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT COUNT(*) AS c FROM channel_codes").fetchone()
    if row and row["c"] and row["c"] > 0:
        return
    from .channel_seeds import CHANNEL_SEEDS

    now = now_str()
    conn.executemany(
        """
        INSERT INTO channel_codes (
            code, name_zh, name_en, country, category, note, dps_channel_name,
            sort_order, is_active, created_time, updated_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        [
            (
                code,
                name_zh,
                name_en or code,
                country,
                category,
                note,
                dps,
                order,
                now,
                now,
            )
            for code, name_zh, name_en, country, category, note, dps, order in CHANNEL_SEEDS
        ],
    )


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


def _sync_exception_codes(conn: sqlite3.Connection) -> None:
    """补齐新增异常类型（不覆盖已有记录）。"""
    table = "shipment_exception_codes"
    now = now_str()
    for code, zh, en, order in _EXCEPTION_SEEDS:
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {table} (
                code, name_zh, name_en, sort_order, is_active, created_time, updated_time
            ) VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (code, zh, en, order, now, now),
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


def _sync_route_status_codes(conn: sqlite3.Connection) -> None:
    """幂等写入 DPS 轨迹细状态映射；非关键节点（如信息传递）is_active=0。"""
    table = "shipment_route_status_codes"
    now = now_str()
    for code, dps, zh, en, order, is_milestone in ROUTE_STATUS_SEEDS:
        active = 1 if is_milestone else 0
        existing = conn.execute(
            f"SELECT code FROM {table} WHERE code = ?",
            (code,),
        ).fetchone()
        if existing:
            conn.execute(
                f"""
                UPDATE {table}
                SET dps_status = ?, name_zh = ?, name_en = ?, sort_order = ?,
                    is_active = ?, updated_time = ?
                WHERE code = ?
                """,
                (dps, zh, en, order, active, now, code),
            )
        else:
            conn.execute(
                f"""
                INSERT INTO {table} (
                    code, dps_status, name_zh, name_en, sort_order, is_active,
                    created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (code, dps, zh, en, order, active, now, now),
            )


def list_code_tables() -> Iterable[str]:
    return (name for name, _ in _CODE_TABLE_DEFS)
