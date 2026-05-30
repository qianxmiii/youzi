"""业务码表 CRUD（channel / country / address / carrier / port / status）。"""

from __future__ import annotations

import sqlite3
from typing import Any

from .channel_seeds import CHANNEL_CATEGORIES
from .code_tables import list_code_tables
from .connection import Database
from .datetime_util import now_str

_ALLOWED_TABLES = frozenset(list_code_tables())

_TABLE_LABELS: dict[str, str] = {
    "channel_codes": "渠道",
    "country_codes": "国家",
    "address_codes": "地址代码",
    "carrier_codes": "承运商",
    "port_codes": "港口",
    "shipment_status_codes": "运单状态",
    "shipment_exception_codes": "运单异常",
}

_PORT_TYPES = frozenset({"origin", "destination", "both"})


def table_label(table: str) -> str:
    return _TABLE_LABELS.get(table, table)


def validate_table(table: str) -> str:
    name = table.strip()
    if name not in _ALLOWED_TABLES:
        raise ValueError(f"未知码表: {table}")
    return name


def list_table_meta() -> list[dict[str, Any]]:
    return [
        {
            "table": name,
            "label": _TABLE_LABELS[name],
            "hasPortType": name == "port_codes",
            "hasChannelFields": name == "channel_codes",
        }
        for name in sorted(_ALLOWED_TABLES)
    ]


def _row_to_api(table: str, row: sqlite3.Row) -> dict[str, Any]:
    out: dict[str, Any] = {
        "code": row["code"],
        "nameZh": row["name_zh"],
        "nameEn": row["name_en"],
        "sortOrder": row["sort_order"],
        "isActive": bool(row["is_active"]),
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }
    if table == "port_codes":
        out["portType"] = row["port_type"]
    if table == "channel_codes":
        out["country"] = row["country"] if "country" in row.keys() else ""
        out["category"] = row["category"] if "category" in row.keys() else ""
        out["note"] = row["note"] if "note" in row.keys() else ""
    return out


class CodeTablesRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_rows(
        self,
        table: str,
        *,
        search: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        t = validate_table(table)
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        conditions: list[str] = []
        params: list[Any] = []
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append("(code LIKE ? OR name_zh LIKE ? OR name_en LIKE ?)")
            params.extend([q, q, q])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {t} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT * FROM {t} {where}
                ORDER BY sort_order ASC, code ASC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return {
            "table": t,
            "label": table_label(t),
            "items": [_row_to_api(t, r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_row(self, table: str, code: str) -> dict[str, Any] | None:
        t = validate_table(table)
        c = code.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {t} WHERE code = ?",
                (c,),
            ).fetchone()
        return _row_to_api(t, row) if row else None

    def insert_row(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        t = validate_table(table)
        payload = self._normalize_payload(t, data)
        code = payload["code"]
        now = now_str()
        with self._database.lock:
            if t == "port_codes":
                self._conn.execute(
                    f"""
                    INSERT INTO {t} (
                        code, name_zh, name_en, port_type,
                        sort_order, is_active, created_time, updated_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        payload["name_zh"],
                        payload["name_en"],
                        payload["port_type"],
                        payload["sort_order"],
                        payload["is_active"],
                        now,
                        now,
                    ),
                )
            elif t == "channel_codes":
                self._conn.execute(
                    f"""
                    INSERT INTO {t} (
                        code, name_zh, name_en, country, category, note,
                        sort_order, is_active, created_time, updated_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        payload["name_zh"],
                        payload["name_en"],
                        payload["country"],
                        payload["category"],
                        payload["note"],
                        payload["sort_order"],
                        payload["is_active"],
                        now,
                        now,
                    ),
                )
            else:
                self._conn.execute(
                    f"""
                    INSERT INTO {t} (
                        code, name_zh, name_en, sort_order, is_active,
                        created_time, updated_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        payload["name_zh"],
                        payload["name_en"],
                        payload["sort_order"],
                        payload["is_active"],
                        now,
                        now,
                    ),
                )
            self._conn.commit()
        row = self.get_row(t, code)
        if row is None:
            raise RuntimeError("插入后读取失败")
        return row

    def update_row(self, table: str, code: str, data: dict[str, Any]) -> dict[str, Any]:
        t = validate_table(table)
        c = code.strip()
        payload = self._normalize_payload(t, data, for_update=True)
        sets = ["name_zh = ?", "name_en = ?", "sort_order = ?", "is_active = ?", "updated_time = ?"]
        vals: list[Any] = [
            payload["name_zh"],
            payload["name_en"],
            payload["sort_order"],
            payload["is_active"],
            now_str(),
        ]
        if t == "port_codes":
            sets.insert(2, "port_type = ?")
            vals.insert(2, payload["port_type"])
        if t == "channel_codes":
            sets[1:1] = ["country = ?", "category = ?", "note = ?"]
            vals[1:1] = [payload["country"], payload["category"], payload["note"]]
        vals.append(c)
        with self._database.lock:
            cur = self._conn.execute(
                f"UPDATE {t} SET {', '.join(sets)} WHERE code = ?",
                vals,
            )
            self._conn.commit()
            if cur.rowcount == 0:
                raise KeyError(c)
        row = self.get_row(t, c)
        if row is None:
            raise KeyError(c)
        return row

    def upsert_row(self, table: str, data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        t = validate_table(table)
        payload = self._normalize_payload(t, data)
        code = payload["code"]
        existing = self.get_row(t, code)
        if existing is None:
            return self.insert_row(t, payload), True
        return self.update_row(t, code, payload), False

    def delete_row(self, table: str, code: str) -> bool:
        t = validate_table(table)
        with self._database.lock:
            cur = self._conn.execute(f"DELETE FROM {t} WHERE code = ?", (code.strip(),))
            self._conn.commit()
            return cur.rowcount > 0

    def _normalize_payload(
        self,
        table: str,
        data: dict[str, Any],
        *,
        for_update: bool = False,
    ) -> dict[str, Any]:
        code = (data.get("code") or data.get("Code") or "").strip()
        if not for_update and not code:
            raise ValueError("编码 code 不能为空")
        name_zh = (data.get("name_zh") or data.get("nameZh") or "").strip()
        name_en = (data.get("name_en") or data.get("nameEn") or "").strip()
        sort_order = data.get("sort_order", data.get("sortOrder", 0))
        try:
            sort_order = int(sort_order)
        except (TypeError, ValueError):
            sort_order = 0
        is_active = data.get("is_active", data.get("isActive", True))
        if isinstance(is_active, str):
            is_active = is_active.strip().lower() in ("1", "true", "yes", "y", "是", "启用")
        is_active = 1 if is_active else 0
        out: dict[str, Any] = {
            "code": code,
            "name_zh": name_zh,
            "name_en": name_en,
            "sort_order": sort_order,
            "is_active": is_active,
        }
        if table == "port_codes":
            port_type = (data.get("port_type") or data.get("portType") or "both").strip().lower()
            if port_type not in _PORT_TYPES:
                raise ValueError("port_type 须为 origin / destination / both")
            out["port_type"] = port_type
        if table == "channel_codes":
            country = (data.get("country") or "").strip()
            category = (data.get("category") or "").strip()
            note = (data.get("note") or "").strip()
            if category and category not in CHANNEL_CATEGORIES:
                raise ValueError(f"大类须为: {' / '.join(CHANNEL_CATEGORIES)}")
            out["country"] = country
            out["category"] = category
            out["note"] = note
        return out
