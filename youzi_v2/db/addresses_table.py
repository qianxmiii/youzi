"""
第三方海外仓 / 商私地址（Legacy）：客户、产品、国家、地址行、商业/住宅、偏远等。
平台仓库地址（AMZ/WFS）见 addresses_warehouse 表。
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

# 历史迁移列（旧版曾把仓库字段写入 addresses，数据已迁至 addresses_warehouse）
_LEGACY_EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("warehouse_code", "TEXT NOT NULL DEFAULT ''"),
    ("address_type", "TEXT NOT NULL DEFAULT ''"),
    ("country_code", "TEXT NOT NULL DEFAULT ''"),
    ("state", "TEXT NOT NULL DEFAULT ''"),
    ("city", "TEXT NOT NULL DEFAULT ''"),
    ("address_line1", "TEXT NOT NULL DEFAULT ''"),
    ("address_line2", "TEXT NOT NULL DEFAULT ''"),
    ("address_line3", "TEXT NOT NULL DEFAULT ''"),
)


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE_NAME,),
    )
    if cur.fetchone() is None:
        conn.execute(_CREATE_SQL)

    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
    legacy_migrations = (
        ("customer", "ALTER TABLE addresses ADD COLUMN customer TEXT NOT NULL DEFAULT '00'"),
        ("product_name", "ALTER TABLE addresses ADD COLUMN product_name TEXT NOT NULL DEFAULT '00'"),
        ("country", "ALTER TABLE addresses ADD COLUMN country TEXT NOT NULL DEFAULT ''"),
        ("address_line", "ALTER TABLE addresses ADD COLUMN address_line TEXT NOT NULL DEFAULT ''"),
        ("postcode", "ALTER TABLE addresses ADD COLUMN postcode TEXT NOT NULL DEFAULT ''"),
        ("company", "ALTER TABLE addresses ADD COLUMN company TEXT NOT NULL DEFAULT ''"),
        ("contact", "ALTER TABLE addresses ADD COLUMN contact TEXT NOT NULL DEFAULT ''"),
        ("phone", "ALTER TABLE addresses ADD COLUMN phone TEXT NOT NULL DEFAULT ''"),
        ("is_commercial", "ALTER TABLE addresses ADD COLUMN is_commercial INTEGER NOT NULL DEFAULT 1"),
        ("is_remote", "ALTER TABLE addresses ADD COLUMN is_remote INTEGER NOT NULL DEFAULT 0"),
        ("sort_order", "ALTER TABLE addresses ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"),
        ("is_default", "ALTER TABLE addresses ADD COLUMN is_default INTEGER NOT NULL DEFAULT 0"),
    )
    for col, ddl in legacy_migrations:
        if col not in cols:
            conn.execute(ddl)
            cols.add(col)

    for col_name, col_def in _LEGACY_EXTRA_COLUMNS:
        if col_name not in cols:
            conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {col_name} {col_def}")


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
            "US",
            "123 Main Street, New York",
            "10001",
            "Example Corp",
            "John Doe",
            "+1-555-0100",
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
        "postcode": row["postcode"],
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


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "customer": (data.get("customer") or "00").strip()[:200] or "00",
        "product_name": (
            data.get("product_name") or data.get("productName") or "00"
        ).strip()[:200]
        or "00",
        "country": (data.get("country") or "").strip()[:50],
        "address_line": (
            data.get("address_line") or data.get("address") or ""
        ).strip()[:500],
        "postcode": (
            data.get("postcode")
            or data.get("postalCode")
            or data.get("postal_code")
            or ""
        ).strip()[:50],
        "company": (data.get("company") or "").strip()[:200],
        "contact": (data.get("contact") or "").strip()[:200],
        "phone": (data.get("phone") or "").strip()[:80],
        "is_commercial": _bool_int(
            data.get("is_commercial", data.get("isCommercial", True))
        ),
        "is_remote": _bool_int(data.get("is_remote", data.get("isRemote", False))),
    }


class AddressesRepository:
    """addresses 表 CRUD（第三方海外仓 / 商私地址）。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_rows(
        self,
        *,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        conditions: list[str] = []
        params: list[Any] = []
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append(
                """(
                    customer LIKE ? OR product_name LIKE ? OR company LIKE ? OR contact LIKE ?
                    OR country LIKE ? OR address_line LIKE ? OR postcode LIKE ? OR phone LIKE ?
                )"""
            )
            params.extend([q] * 8)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query_limit: int | None = None
        query_offset = 0
        if limit is not None:
            query_limit = max(1, min(limit, 500))
            query_offset = max(0, offset)

        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {TABLE_NAME} {where}",
                params,
            ).fetchone()["c"]
            sql = f"""
                SELECT * FROM {TABLE_NAME}
                {where}
                ORDER BY sort_order ASC, datetime(updated_at) DESC
            """
            query_params = list(params)
            if query_limit is not None:
                sql += " LIMIT ? OFFSET ?"
                query_params.extend([query_limit, query_offset])
            rows = self._conn.execute(sql, query_params).fetchall()
            return {
                "items": [_row_to_api_dict(r) for r in rows],
                "total": total,
            }

    def insert_row(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = _normalize_payload(data)
        now = datetime.now().isoformat(timespec="seconds")
        rid = str(uuid.uuid4())
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
                    payload["customer"],
                    payload["product_name"],
                    payload["country"],
                    payload["address_line"],
                    payload["postcode"],
                    payload["company"],
                    payload["contact"],
                    payload["phone"],
                    payload["is_commercial"],
                    payload["is_remote"],
                    now,
                    now,
                ),
            )
            self._conn.commit()
        row = self._conn.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (rid,)).fetchone()
        return _row_to_api_dict(row) if row else {}

    def update_row(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = _normalize_payload(data)
        now = datetime.now().isoformat(timespec="seconds")
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
                    payload["customer"],
                    payload["product_name"],
                    payload["country"],
                    payload["address_line"],
                    payload["postcode"],
                    payload["company"],
                    payload["contact"],
                    payload["phone"],
                    payload["is_commercial"],
                    payload["is_remote"],
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
