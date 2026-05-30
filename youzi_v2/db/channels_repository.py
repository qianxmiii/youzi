"""渠道管理（channel_codes 扩展字段）。"""

from __future__ import annotations

import sqlite3
from typing import Any

from .channel_seeds import CHANNEL_CATEGORIES, CHANNEL_SEEDS, LEGACY_CHANNEL_CATEGORY_MAP
from .connection import Database
from .datetime_util import now_str

TABLE_NAME = "channel_codes"


def _row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "code": row["code"],
        "nameZh": row["name_zh"] or "",
        "nameEn": row["name_en"] or "",
        "country": row["country"] if "country" in row.keys() else "",
        "category": row["category"] if "category" in row.keys() else "",
        "note": row["note"] if "note" in row.keys() else "",
        "sortOrder": row["sort_order"],
        "isActive": bool(row["is_active"]),
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


class ChannelsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    @staticmethod
    def categories() -> list[str]:
        return list(CHANNEL_CATEGORIES)

    def list_rows(
        self,
        *,
        search: str | None = None,
        country: str | None = None,
        category: str | None = None,
        active_only: bool | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        conditions: list[str] = []
        params: list[Any] = []
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append(
                "(code LIKE ? OR name_zh LIKE ? OR name_en LIKE ? OR country LIKE ? OR note LIKE ?)"
            )
            params.extend([q, q, q, q, q])
        if country and country.strip():
            conditions.append("country = ?")
            params.append(country.strip())
        if category and category.strip():
            conditions.append("category = ?")
            params.append(category.strip())
        if active_only is True:
            conditions.append("is_active = 1")
        elif active_only is False:
            conditions.append("is_active = 0")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {TABLE_NAME} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME} {where}
                ORDER BY sort_order ASC, code ASC
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

    def get_row(self, code: str) -> dict[str, Any] | None:
        c = code.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE code = ?",
                (c,),
            ).fetchone()
        return _row_to_api(row) if row else None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_payload(data)
        code = payload["code"]
        if self.get_row(code):
            raise ValueError(f"渠道已存在: {code}")
        now = now_str()
        with self._database.lock:
            self._conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
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
            self._conn.commit()
        row = self.get_row(code)
        if row is None:
            raise RuntimeError("插入后读取失败")
        return row

    def update(self, code: str, data: dict[str, Any]) -> dict[str, Any]:
        c = code.strip()
        payload = self._normalize_payload(data, for_update=True)
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME} SET
                    name_zh = ?, name_en = ?, country = ?, category = ?, note = ?,
                    sort_order = ?, is_active = ?, updated_time = ?
                WHERE code = ?
                """,
                (
                    payload["name_zh"],
                    payload["name_en"],
                    payload["country"],
                    payload["category"],
                    payload["note"],
                    payload["sort_order"],
                    payload["is_active"],
                    now_str(),
                    c,
                ),
            )
            self._conn.commit()
            if cur.rowcount == 0:
                raise KeyError(c)
        row = self.get_row(c)
        if row is None:
            raise KeyError(c)
        return row

    def delete(self, code: str) -> bool:
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE code = ?",
                (code.strip(),),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def migrate_legacy_categories(self) -> int:
        """将旧版「海运/快递」等大类迁移为快船/普船/卡航/铁路/空运。"""
        changed = 0
        with self._database.lock:
            for old, new in LEGACY_CHANNEL_CATEGORY_MAP.items():
                cur = self._conn.execute(
                    f"UPDATE {TABLE_NAME} SET category = ? WHERE category = ?",
                    (new, old),
                )
                changed += cur.rowcount
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET category = '快船'
                WHERE category = '普船'
                  AND (name_zh LIKE '%快船%' OR code LIKE '%Rapid%' OR code LIKE '%Fast%')
                """
            )
            changed += cur.rowcount
            self._conn.commit()
        return changed

    def seed_defaults(self) -> dict[str, int]:
        """写入内置渠道列表（已存在的 code 仅更新扩展字段，不删用户数据）。"""
        self.migrate_legacy_categories()
        now = now_str()
        inserted = 0
        updated = 0
        with self._database.lock:
            for code, name_zh, country, category, note, sort_order in CHANNEL_SEEDS:
                row = self._conn.execute(
                    f"SELECT code FROM {TABLE_NAME} WHERE code = ?",
                    (code,),
                ).fetchone()
                if row:
                    self._conn.execute(
                        f"""
                        UPDATE {TABLE_NAME} SET
                            name_zh = ?, name_en = ?, country = ?, category = ?, note = ?,
                            sort_order = ?, updated_time = ?
                        WHERE code = ?
                        """,
                        (name_zh, code, country, category, note, sort_order, now, code),
                    )
                    updated += 1
                else:
                    self._conn.execute(
                        f"""
                        INSERT INTO {TABLE_NAME} (
                            code, name_zh, name_en, country, category, note,
                            sort_order, is_active, created_time, updated_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                        """,
                        (code, name_zh, code, country, category, note, sort_order, now, now),
                    )
                    inserted += 1
            self._conn.commit()
        return {"inserted": inserted, "updated": updated, "total": len(CHANNEL_SEEDS)}

    def _normalize_payload(
        self,
        data: dict[str, Any],
        *,
        for_update: bool = False,
    ) -> dict[str, Any]:
        code = (data.get("code") or "").strip()
        if not for_update and not code:
            raise ValueError("渠道编码不能为空")
        name_zh = (data.get("name_zh") or data.get("nameZh") or "").strip()
        name_en = (data.get("name_en") or data.get("nameEn") or code).strip()
        country = (data.get("country") or "").strip()
        category = (data.get("category") or "").strip()
        note = (data.get("note") or "").strip()
        if category and category not in CHANNEL_CATEGORIES:
            raise ValueError(f"大类须为: {' / '.join(CHANNEL_CATEGORIES)}")
        sort_order = data.get("sort_order", data.get("sortOrder", 0))
        try:
            sort_order = int(sort_order)
        except (TypeError, ValueError):
            sort_order = 0
        is_active = data.get("is_active", data.get("isActive", True))
        if isinstance(is_active, str):
            is_active = is_active.strip().lower() in ("1", "true", "yes", "y", "是", "启用")
        return {
            "code": code,
            "name_zh": name_zh,
            "name_en": name_en,
            "country": country,
            "category": category,
            "note": note,
            "sort_order": sort_order,
            "is_active": 1 if is_active else 0,
        }
