"""客户地址簿查询与保存。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from .customer_addresses_table import ADDRESS_KINDS, TABLE_NAME
from .customers_table import TABLE_NAME as CUSTOMERS_TABLE
from .datetime_util import now_str


def _text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "customerName": row["customer_name"] or "",
        "label": row["label"] or "",
        "consigneeName": row["consignee_name"] or "",
        "company": row["company"] or "",
        "phone": row["phone"] or "",
        "email": row["email"] or "",
        "country": row["country"] or "",
        "address": row["address"] or "",
        "postcode": row["postcode"] or "",
        "addressKind": row["address_kind"] or "",
        "isRemote": bool(row["is_remote"]),
        "note": row["note"] or "",
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


class CustomerAddressesRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _canonical_customer(self, name: str) -> str:
        clean = (name or "").strip()
        if not clean:
            raise ValueError("客户名不能为空")
        row = self._conn.execute(
            f"""
            SELECT customer_name FROM {CUSTOMERS_TABLE}
            WHERE customer_name = ? COLLATE NOCASE
            """,
            (clean,),
        ).fetchone()
        if row is None:
            raise ValueError("客户不存在，请先在客户管理中添加")
        return str(row["customer_name"])

    def _payload(self, data: dict[str, Any]) -> dict[str, Any]:
        kind = _text(data.get("address_kind") or data.get("addressKind"), 32).upper()
        if kind not in ADDRESS_KINDS:
            raise ValueError("地址类型须为海外仓、商业或住宅")
        country = _text(data.get("country"), 64)
        address = _text(data.get("address"), 1000)
        if not country:
            raise ValueError("国家不能为空")
        if not address:
            raise ValueError("收件人地址不能为空")
        remote = data.get("is_remote")
        if remote is None:
            remote = data.get("isRemote")
        return {
            "customer_name": self._canonical_customer(
                str(data.get("customer_name") or data.get("customerName") or "")
            ),
            "label": _text(data.get("label"), 120),
            "consignee_name": _text(
                data.get("consignee_name") or data.get("consigneeName"), 120
            ),
            "company": _text(data.get("company"), 200),
            "phone": _text(data.get("phone"), 80),
            "email": _text(data.get("email"), 200),
            "country": country,
            "address": address,
            "postcode": _text(data.get("postcode"), 32),
            "address_kind": kind,
            "is_remote": 1 if bool(remote) else 0,
            "note": _text(data.get("note"), 500),
        }

    def list_rows(
        self,
        *,
        customer: str | None = None,
        address_kind: str | None = None,
        remote: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 10_000))
        offset = max(0, offset)
        conditions: list[str] = []
        params: list[Any] = []
        if customer and customer.strip():
            conditions.append("customer_name = ? COLLATE NOCASE")
            params.append(customer.strip())
        kind = (address_kind or "").strip().upper()
        if kind:
            if kind not in ADDRESS_KINDS:
                raise ValueError("地址类型无效")
            conditions.append("address_kind = ?")
            params.append(kind)
        if remote is True:
            conditions.append("is_remote = 1")
        elif remote is False:
            conditions.append("is_remote = 0")
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append(
                "("
                "label LIKE ? OR consignee_name LIKE ? OR company LIKE ? "
                "OR phone LIKE ? OR email LIKE ? OR address LIKE ? "
                "OR postcode LIKE ? OR note LIKE ?"
                ")"
            )
            params.extend([q, q, q, q, q, q, q, q])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {TABLE_NAME} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                {where}
                ORDER BY datetime(updated_time) DESC, customer_name, id
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return {
            "items": [_row_to_api(row) for row in rows],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    def insert_row(self, data: dict[str, Any]) -> dict[str, Any]:
        now = now_str()
        rid = str(uuid.uuid4())
        with self._database.lock:
            payload = self._payload(data)
            self._conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, customer_name, label, consignee_name, company, phone, email,
                    country, address, postcode, address_kind, is_remote, note,
                    created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    payload["customer_name"],
                    payload["label"],
                    payload["consignee_name"],
                    payload["company"],
                    payload["phone"],
                    payload["email"],
                    payload["country"],
                    payload["address"],
                    payload["postcode"],
                    payload["address_kind"],
                    payload["is_remote"],
                    payload["note"],
                    now,
                    now,
                ),
            )
            self._conn.commit()
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE id = ?",
                (rid,),
            ).fetchone()
        if row is None:
            raise RuntimeError("地址写入失败")
        return _row_to_api(row)

    def update_row(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        rid = item_id.strip()
        now = now_str()
        with self._database.lock:
            payload = self._payload(data)
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET customer_name = ?, label = ?, consignee_name = ?, company = ?,
                    phone = ?, email = ?, country = ?, address = ?, postcode = ?,
                    address_kind = ?, is_remote = ?, note = ?, updated_time = ?
                WHERE id = ?
                """,
                (
                    payload["customer_name"],
                    payload["label"],
                    payload["consignee_name"],
                    payload["company"],
                    payload["phone"],
                    payload["email"],
                    payload["country"],
                    payload["address"],
                    payload["postcode"],
                    payload["address_kind"],
                    payload["is_remote"],
                    payload["note"],
                    now,
                    rid,
                ),
            )
            if cur.rowcount == 0:
                raise KeyError(rid)
            self._conn.commit()
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE id = ?",
                (rid,),
            ).fetchone()
        if row is None:
            raise KeyError(rid)
        return _row_to_api(row)

    def delete_row(self, item_id: str) -> bool:
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE id = ?",
                (item_id.strip(),),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def delete_many(self, ids: list[str]) -> dict[str, int]:
        clean = [item.strip() for item in ids if item and item.strip()]
        if not clean:
            raise ValueError("请选择地址")
        if len(clean) > 500:
            raise ValueError("一次最多删除 500 条")
        placeholders = ", ".join("?" for _ in clean)
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE id IN ({placeholders})",
                clean,
            )
            self._conn.commit()
            return {"deleted": int(cur.rowcount)}
