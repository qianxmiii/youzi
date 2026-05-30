"""
平台仓库地址簿（AMZ / WFS）：仓库代码、收件人、国家/州省/城市、地址行、电话、备注等。
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Any

from .app_settings_table import get_setting, set_setting
from .connection import Database

TABLE_NAME = "addresses_warehouse"
ADDRESS_TYPES = frozenset({"AMZ", "WFS"})
_MIGRATION_KEY = "addresses_warehouse_migrated_v1"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    warehouse_code TEXT NOT NULL DEFAULT '',
    address_type TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    contact TEXT NOT NULL DEFAULT '',
    country_code TEXT NOT NULL DEFAULT '',
    postcode TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    address_line1 TEXT NOT NULL DEFAULT '',
    address_line2 TEXT NOT NULL DEFAULT '',
    address_line3 TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    note1 TEXT NOT NULL DEFAULT '',
    note2 TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
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
        conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_warehouse_code
            ON {TABLE_NAME}(warehouse_code COLLATE NOCASE)
            """
        )
        conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_country_code
            ON {TABLE_NAME}(country_code)
            """
        )
    migrate_from_addresses(conn)


    conn.execute(
        f"UPDATE {TABLE_NAME} SET address_type = 'AMZ' WHERE UPPER(TRIM(address_type)) = 'FBA'"
    )


def migrate_from_addresses(conn: sqlite3.Connection) -> None:
    if get_setting(conn, _MIGRATION_KEY) == "1":
        return

    legacy_cols = {
        r[1] for r in conn.execute("PRAGMA table_info(addresses)").fetchall()
    }
    if "warehouse_code" not in legacy_cols:
        set_setting(conn, _MIGRATION_KEY, "1")
        return

    rows = conn.execute(
        """
        SELECT * FROM addresses
        WHERE TRIM(COALESCE(warehouse_code, '')) != ''
           OR UPPER(TRIM(COALESCE(address_type, ''))) IN ('AMZ', 'WFS', 'FBA')
        """
    ).fetchall()

    for row in rows:
        warehouse_code = (
            (row["warehouse_code"] if "warehouse_code" in row.keys() else "")
            or (row["address_line"] if "address_line" in row.keys() else "")
            or ""
        ).strip()
        if not warehouse_code:
            continue
        existing = conn.execute(
            f"""
            SELECT id FROM {TABLE_NAME}
            WHERE TRIM(warehouse_code) = ? COLLATE NOCASE
            LIMIT 1
            """,
            (warehouse_code,),
        ).fetchone()
        if existing:
            continue

        country_code = (
            (row["country_code"] if "country_code" in row.keys() else "")
            or (row["country"] if "country" in row.keys() else "")
            or ""
        ).strip()
        address_line1 = (
            (row["address_line1"] if "address_line1" in row.keys() else "")
            or (row["address_line"] if "address_line" in row.keys() else "")
            or ""
        ).strip()
        address_type = (
            row["address_type"] if "address_type" in row.keys() else ""
        ).strip().upper()
        if address_type == "FBA":
            address_type = "AMZ"
        if address_type and address_type not in ADDRESS_TYPES:
            address_type = ""

        conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, warehouse_code, address_type, company, contact, country_code,
                postcode, state, city, address_line1, address_line2, address_line3,
                phone, note1, note2, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                warehouse_code,
                address_type,
                row["company"],
                row["contact"],
                country_code,
                row["postcode"],
                row["state"] if "state" in row.keys() else "",
                row["city"] if "city" in row.keys() else "",
                address_line1,
                row["address_line2"] if "address_line2" in row.keys() else "",
                row["address_line3"] if "address_line3" in row.keys() else "",
                row["phone"],
                "",
                "",
                row["sort_order"] if "sort_order" in row.keys() else 0,
                row["created_at"],
                row["updated_at"],
            ),
        )

    set_setting(conn, _MIGRATION_KEY, "1")


def seed_if_empty(conn: sqlite3.Connection) -> None:
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {TABLE_NAME}").fetchone()
    if row and row["c"] and row["c"] > 0:
        return
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        f"""
        INSERT INTO {TABLE_NAME} (
            id, warehouse_code, address_type, company, contact, country_code,
            postcode, state, city, address_line1, address_line2, address_line3,
            phone, note1, note2, sort_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            "DFW2",
            "AMZ",
            "Example Corp",
            "John Doe",
            "US",
            "75261",
            "TX",
            "Dallas",
            "1234 Warehouse Blvd",
            "",
            "",
            "+1-555-0100",
            "",
            "",
            0,
            now,
            now,
        ),
    )


def _row_get(row: sqlite3.Row, key: str, default: str = "") -> str:
    return row[key] if key in row.keys() else default


def _row_to_api_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "warehouseCode": row["warehouse_code"],
        "addressType": row["address_type"],
        "company": row["company"],
        "contact": row["contact"],
        "countryCode": row["country_code"],
        "postalCode": row["postcode"],
        "state": row["state"],
        "city": row["city"],
        "addressLine1": row["address_line1"],
        "addressLine2": row["address_line2"],
        "addressLine3": row["address_line3"],
        "phone": row["phone"],
        "note1": row["note1"],
        "note2": row["note2"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    address_type = (
        data.get("address_type") or data.get("addressType") or ""
    ).strip().upper()
    if address_type == "FBA":
        address_type = "AMZ"
    if address_type and address_type not in ADDRESS_TYPES:
        raise ValueError("地址类型须为 AMZ 或 WFS")

    warehouse_code = (
        data.get("warehouse_code") or data.get("warehouseCode") or ""
    ).strip()[:80]
    if not warehouse_code:
        raise ValueError("仓库代码不能为空")

    return {
        "warehouse_code": warehouse_code,
        "address_type": address_type,
        "company": (data.get("company") or "").strip()[:200],
        "contact": (data.get("contact") or "").strip()[:200],
        "country_code": (
            data.get("country_code") or data.get("countryCode") or ""
        ).strip()[:20],
        "postcode": (
            data.get("postcode")
            or data.get("postalCode")
            or data.get("postal_code")
            or ""
        ).strip()[:50],
        "state": (data.get("state") or "").strip()[:100],
        "city": (data.get("city") or "").strip()[:100],
        "address_line1": (data.get("address_line1") or data.get("addressLine1") or "").strip()[:500],
        "address_line2": (data.get("address_line2") or data.get("addressLine2") or "").strip()[:500],
        "address_line3": (data.get("address_line3") or data.get("addressLine3") or "").strip()[:500],
        "phone": (data.get("phone") or "").strip()[:80],
        "note1": (data.get("note1") or data.get("note_1") or "").strip()[:500],
        "note2": (data.get("note2") or data.get("note_2") or "").strip()[:500],
    }


class AddressesWarehouseRepository:
    """addresses_warehouse 表 CRUD。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_rows(
        self,
        *,
        search: str | None = None,
        address_type: str | None = None,
        country_code: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        conditions: list[str] = []
        params: list[Any] = []
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append(
                """(
                    warehouse_code LIKE ? OR company LIKE ? OR contact LIKE ?
                    OR country_code LIKE ? OR city LIKE ? OR state LIKE ?
                    OR address_line1 LIKE ? OR address_line2 LIKE ? OR address_line3 LIKE ?
                    OR postcode LIKE ? OR phone LIKE ? OR note1 LIKE ? OR note2 LIKE ?
                )"""
            )
            params.extend([q] * 13)
        if address_type and address_type.strip():
            conditions.append("address_type = ?")
            params.append(address_type.strip().upper())
        if country_code and country_code.strip():
            conditions.append("TRIM(country_code) = ? COLLATE NOCASE")
            params.append(country_code.strip())
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

    def list_filter_options(self) -> dict[str, Any]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT DISTINCT TRIM(country_code) AS cc
                FROM {TABLE_NAME}
                WHERE TRIM(COALESCE(country_code, '')) != ''
                ORDER BY cc COLLATE NOCASE
                """
            ).fetchall()
        return {"countries": [r["cc"] for r in rows if r["cc"]]}

    def insert_row(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = _normalize_payload(data)
        now = datetime.now().isoformat(timespec="seconds")
        rid = str(uuid.uuid4())
        with self._database.lock:
            self._conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, warehouse_code, address_type, company, contact, country_code,
                    postcode, state, city, address_line1, address_line2, address_line3,
                    phone, note1, note2, sort_order, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    rid,
                    payload["warehouse_code"],
                    payload["address_type"],
                    payload["company"],
                    payload["contact"],
                    payload["country_code"],
                    payload["postcode"],
                    payload["state"],
                    payload["city"],
                    payload["address_line1"],
                    payload["address_line2"],
                    payload["address_line3"],
                    payload["phone"],
                    payload["note1"],
                    payload["note2"],
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
                    warehouse_code = ?, address_type = ?, company = ?, contact = ?,
                    country_code = ?, postcode = ?, state = ?, city = ?,
                    address_line1 = ?, address_line2 = ?, address_line3 = ?,
                    phone = ?, note1 = ?, note2 = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload["warehouse_code"],
                    payload["address_type"],
                    payload["company"],
                    payload["contact"],
                    payload["country_code"],
                    payload["postcode"],
                    payload["state"],
                    payload["city"],
                    payload["address_line1"],
                    payload["address_line2"],
                    payload["address_line3"],
                    payload["phone"],
                    payload["note1"],
                    payload["note2"],
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

    def find_id_by_warehouse_code(self, warehouse_code: str) -> str | None:
        code = warehouse_code.strip()
        if not code:
            return None
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT id FROM {TABLE_NAME}
                WHERE TRIM(warehouse_code) = ? COLLATE NOCASE
                LIMIT 1
                """,
                (code,),
            ).fetchone()
        return row["id"] if row else None

    def upsert_row(self, data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        payload = _normalize_payload(data)
        existing_id = self.find_id_by_warehouse_code(payload["warehouse_code"])
        if existing_id:
            return self.update_row(existing_id, data), False
        return self.insert_row(data), True
