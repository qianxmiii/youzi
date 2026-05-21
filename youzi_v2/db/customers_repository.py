"""客户管理：从运单同步客户名，VIP 标识。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .customers_table import TABLE_NAME
from .shipments_table import TABLE_NAME as SHIPMENTS_TABLE


def _normalize_name(name: str) -> str:
    return name.strip()


def _row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "customerName": row["customer_name"],
        "isVip": bool(row["is_vip"]),
        "note": row["note"] or "",
        "shipmentCount": int(row["shipment_count"] or 0),
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


class CustomersRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def vip_customer_name_set(self) -> set[str]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT customer_name FROM {TABLE_NAME}
                WHERE is_vip = 1
                """,
            ).fetchall()
        return {
            _normalize_name(r["customer_name"])
            for r in rows
            if _normalize_name(r["customer_name"])
        }

    def list_rows(
        self,
        *,
        search: str | None = None,
        vip_only: bool | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        conditions: list[str] = []
        params: list[Any] = []
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append("(customer_name LIKE ? OR note LIKE ?)")
            params.extend([q, q])
        if vip_only is True:
            conditions.append("is_vip = 1")
        elif vip_only is False:
            conditions.append("is_vip = 0")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {TABLE_NAME} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME} {where}
                ORDER BY is_vip DESC, customer_name ASC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return {
            "items": [_row_to_api(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def sync_from_shipments(self) -> dict[str, int]:
        """拉取运单表全部去重客户名写入客户表，并刷新运单数。"""
        now = now_str()
        added = 0
        with self._database.lock:
            names = self._conn.execute(
                f"""
                SELECT DISTINCT TRIM(customer) AS name
                FROM {SHIPMENTS_TABLE}
                WHERE customer IS NOT NULL AND TRIM(customer) != ''
                ORDER BY name
                """
            ).fetchall()
            for row in names:
                name = _normalize_name(row["name"] or "")
                if not name:
                    continue
                cur = self._conn.execute(
                    f"""
                    INSERT OR IGNORE INTO {TABLE_NAME}
                        (id, customer_name, is_vip, note, shipment_count, created_time, updated_time)
                    VALUES (?, ?, 0, '', 0, ?, ?)
                    """,
                    (str(uuid.uuid4()), name, now, now),
                )
                added += cur.rowcount
            self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET shipment_count = (
                    SELECT COUNT(*) FROM {SHIPMENTS_TABLE} s
                    WHERE TRIM(s.customer) = {TABLE_NAME}.customer_name
                ),
                updated_time = ?
                """,
                (now,),
            )
            self._conn.commit()
            total = self._conn.execute(f"SELECT COUNT(*) AS c FROM {TABLE_NAME}").fetchone()[
                "c"
            ]
        return {"added": added, "total": int(total), "fromShipments": len(names)}

    def set_vip(self, item_id: str, is_vip: bool) -> dict[str, Any] | None:
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET is_vip = ?, updated_time = ?
                WHERE id = ?
                """,
                (1 if is_vip else 0, now, item_id.strip()),
            )
            if cur.rowcount == 0:
                return None
            self._conn.commit()
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (item_id.strip(),)
            ).fetchone()
        return _row_to_api(row) if row else None

    def update_note(self, item_id: str, note: str) -> dict[str, Any] | None:
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME} SET note = ?, updated_time = ? WHERE id = ?
                """,
                ((note or "").strip(), now, item_id.strip()),
            )
            if cur.rowcount == 0:
                return None
            self._conn.commit()
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (item_id.strip(),)
            ).fetchone()
        return _row_to_api(row) if row else None

    def create(self, customer_name: str, *, note: str = "", is_vip: bool = False) -> dict[str, Any]:
        name = _normalize_name(customer_name)
        if not name:
            raise ValueError("客户名不能为空")
        rid = str(uuid.uuid4())
        now = now_str()
        with self._database.lock:
            try:
                self._conn.execute(
                    f"""
                    INSERT INTO {TABLE_NAME}
                        (id, customer_name, is_vip, note, shipment_count, created_time, updated_time)
                    VALUES (?, ?, ?, ?, 0, ?, ?)
                    """,
                    (rid, name, 1 if is_vip else 0, (note or "").strip(), now, now),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"客户名已存在：{name}") from exc
            count = self._conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {SHIPMENTS_TABLE}
                WHERE TRIM(customer) = ?
                """,
                (name,),
            ).fetchone()["c"]
            self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET shipment_count = ?, updated_time = ?
                WHERE id = ?
                """,
                (int(count), now_str(), rid),
            )
            self._conn.commit()
        row = self._conn.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (rid,)).fetchone()
        return _row_to_api(row)

    def delete(self, item_id: str) -> bool:
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE id = ?",
                (item_id.strip(),),
            )
            self._conn.commit()
            return cur.rowcount > 0
