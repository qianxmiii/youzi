"""
常用地址簿：每个业务含义独立一列（客户代码、品名、国家、地址行等），便于查询、导出和与 index 页对齐。

说明：不用「一个大字符串」塞全部信息，是因为国家/邮编/门牌或仓库代码在业务上字段语义不同，
拆列才能按条件筛选、统计和生成模板；需要一整段展示时由 API 或前端按需拼接即可。
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Any

from .connection import Database

TABLE_NAME = "addresses"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    customer TEXT NOT NULL DEFAULT '00',
    product_name TEXT NOT NULL DEFAULT '00',
    country TEXT NOT NULL DEFAULT '',
    address_line TEXT NOT NULL DEFAULT '',
    postcode TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    contact TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    is_commercial INTEGER NOT NULL DEFAULT 1,
    is_remote INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE_NAME,),
    )
    if cur.fetchone() is None:
        conn.execute(_CREATE_SQL)
        return

    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
    if "customer" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN customer TEXT NOT NULL DEFAULT '00'"
        )
        if "label" in cols:
            conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET customer = CASE
                    WHEN TRIM(COALESCE(label, '')) = '' THEN '00'
                    ELSE label
                END
                """
            )
    if "product_name" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN product_name TEXT NOT NULL DEFAULT '00'"
        )
    if "country" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN country TEXT NOT NULL DEFAULT ''"
        )
    if "address_line" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN address_line TEXT NOT NULL DEFAULT ''"
        )
    if "postcode" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN postcode TEXT NOT NULL DEFAULT ''"
        )
    if "company" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN company TEXT NOT NULL DEFAULT ''"
        )
    if "contact" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN contact TEXT NOT NULL DEFAULT ''"
        )
    if "phone" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN phone TEXT NOT NULL DEFAULT ''"
        )
    if "is_commercial" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN is_commercial INTEGER NOT NULL DEFAULT 1"
        )
    if "is_remote" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN is_remote INTEGER NOT NULL DEFAULT 0"
        )
    if "sort_order" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
        )
    if "is_default" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN is_default INTEGER NOT NULL DEFAULT 0"
        )


def seed_if_empty(conn: sqlite3.Connection) -> None:
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {TABLE_NAME}").fetchone()
    if row and row["c"] and row["c"] > 0:
        return
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        f"""
        INSERT INTO {TABLE_NAME} (
            id, customer, product_name, country, address_line, postcode,
            company, contact, phone, is_commercial, is_remote,
            sort_order, is_default, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            "00",
            "00",
            "美国",
            "EXAMPLE WAREHOUSE CODE",
            "00000",
            "",
            "",
            "",
            1,
            0,
            0,
            0,
            now,
            now,
        ),
    )


def _row_to_api_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "customer": row["customer"],
        "productName": row["product_name"],
        "country": row["country"],
        "address": row["address_line"],
        "postalCode": row["postcode"],
        "company": row["company"],
        "contact": row["contact"],
        "phone": row["phone"],
        "isCommercial": bool(row["is_commercial"]),
        "isRemote": bool(row["is_remote"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _bool_int(v: Any) -> int:
    return 1 if v else 0


class AddressesRepository:
    """addresses 表：读写在同一模块，便于单独拷贝迁移。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_rows(self) -> list[dict[str, Any]]:
        with self._database.lock:
            rows = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} ORDER BY sort_order ASC, datetime(updated_at) DESC"
            ).fetchall()
            return [_row_to_api_dict(r) for r in rows]

    def insert_row(
        self,
        customer: str,
        product_name: str,
        country: str,
        address_line: str,
        postcode: str,
        company: str,
        contact: str,
        phone: str,
        is_commercial: bool,
        is_remote: bool,
    ) -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")
        rid = str(uuid.uuid4())
        cc = (customer or "").strip()[:200] or "00"
        pn = (product_name or "").strip()[:200] or "00"
        with self._database.lock:
            self._conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, customer, product_name, country, address_line, postcode,
                    company, contact, phone, is_commercial, is_remote,
                    sort_order, is_default, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
                """,
                (
                    rid,
                    cc,
                    pn,
                    (country or "").strip()[:200],
                    (address_line or "").strip()[:500],
                    (postcode or "").strip()[:50],
                    (company or "").strip()[:200],
                    (contact or "").strip()[:200],
                    (phone or "").strip()[:80],
                    _bool_int(is_commercial),
                    _bool_int(is_remote),
                    now,
                    now,
                ),
            )
            self._conn.commit()
        row = self._conn.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (rid,)).fetchone()
        return _row_to_api_dict(row) if row else {}

    def update_row(
        self,
        item_id: str,
        customer: str,
        product_name: str,
        country: str,
        address_line: str,
        postcode: str,
        company: str,
        contact: str,
        phone: str,
        is_commercial: bool,
        is_remote: bool,
    ) -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")
        cc = (customer or "").strip()[:200] or "00"
        pn = (product_name or "").strip()[:200] or "00"
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT id FROM {TABLE_NAME} WHERE id = ?", (item_id,)
            ).fetchone()
            if row is None:
                raise KeyError(item_id)
            self._conn.execute(
                f"""
                UPDATE {TABLE_NAME} SET
                    customer = ?, product_name = ?, country = ?, address_line = ?, postcode = ?,
                    company = ?, contact = ?, phone = ?,
                    is_commercial = ?, is_remote = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    cc,
                    pn,
                    (country or "").strip()[:200],
                    (address_line or "").strip()[:500],
                    (postcode or "").strip()[:50],
                    (company or "").strip()[:200],
                    (contact or "").strip()[:200],
                    (phone or "").strip()[:80],
                    _bool_int(is_commercial),
                    _bool_int(is_remote),
                    now,
                    item_id,
                ),
            )
            self._conn.commit()
        row2 = self._conn.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (item_id,)).fetchone()
        return _row_to_api_dict(row2) if row2 else {}

    def delete_row(self, item_id: str) -> bool:
        with self._database.lock:
            cur = self._conn.execute(f"DELETE FROM {TABLE_NAME} WHERE id = ?", (item_id,))
            self._conn.commit()
            return cur.rowcount > 0
