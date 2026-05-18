"""sys_dict 字典表 CRUD。"""

from __future__ import annotations

import sqlite3
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .dict_table import TABLE_NAME


def _row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "dictType": row["dict_type"],
        "code": row["code"],
        "value": row["value"],
        "desc": row["desc"],
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    key_map = {
        "dictType": "dict_type",
        "dict_type": "dict_type",
        "code": "code",
        "value": "value",
        "desc": "desc",
    }
    out: dict[str, Any] = {}
    for key, value in data.items():
        col = key_map.get(key)
        if col is not None:
            out[col] = value
    return out


class DictRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_rows(
        self,
        *,
        dict_type: str | None = None,
        search: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 1000))
        offset = max(0, offset)
        conditions: list[str] = []
        params: list[Any] = []
        if dict_type and dict_type.strip():
            conditions.append("dict_type = ?")
            params.append(dict_type.strip())
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append(
                "(code LIKE ? OR value LIKE ? OR desc LIKE ? OR dict_type LIKE ?)"
            )
            params.extend([q, q, q, q])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {TABLE_NAME} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME} {where}
                ORDER BY dict_type ASC, code ASC
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

    def list_by_type(self, dict_type: str) -> list[dict[str, Any]]:
        dt = dict_type.strip()
        if not dt:
            return []
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE dict_type = ?
                ORDER BY code ASC
                """,
                (dt,),
            ).fetchall()
        return [_row_to_api(r) for r in rows]

    def get(self, dict_type: str, code: str) -> dict[str, Any] | None:
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE dict_type = ? AND code = ?",
                (dict_type.strip(), code.strip()),
            ).fetchone()
        return _row_to_api(row) if row else None

    def upsert(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = _normalize_payload(data)
        dict_type = (payload.get("dict_type") or "").strip()
        code = (payload.get("code") or "").strip()
        if not dict_type or not code:
            raise ValueError("dict_type 与 code 不能为空")
        value = payload.get("value")
        desc = payload.get("desc")
        now = now_str()
        with self._database.lock:
            existing = self._conn.execute(
                f"SELECT 1 FROM {TABLE_NAME} WHERE dict_type = ? AND code = ?",
                (dict_type, code),
            ).fetchone()
            if existing:
                sets = ["updated_time = ?"]
                vals: list[Any] = [now]
                if value is not None:
                    sets.append("value = ?")
                    vals.append(value)
                if desc is not None:
                    sets.append("desc = ?")
                    vals.append(desc)
                vals.extend([dict_type, code])
                self._conn.execute(
                    f"UPDATE {TABLE_NAME} SET {', '.join(sets)} WHERE dict_type = ? AND code = ?",
                    vals,
                )
            else:
                self._conn.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (
                        dict_type, code, value, desc, created_time, updated_time
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dict_type,
                        code,
                        value if value is not None else "",
                        desc if desc is not None else "",
                        now,
                        now,
                    ),
                )
            self._conn.commit()
        row = self.get(dict_type, code)
        if row is None:
            raise RuntimeError("写入后读取失败")
        return row

    def delete(self, dict_type: str, code: str) -> bool:
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE dict_type = ? AND code = ?",
                (dict_type.strip(), code.strip()),
            )
            self._conn.commit()
            return cur.rowcount > 0
