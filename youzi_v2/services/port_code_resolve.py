"""挂靠港名称 → 港口码表（port_codes）解析，仅用于展示，不写回船期表。"""

from __future__ import annotations

import re
import sqlite3
from typing import Any


def _norm_key(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().casefold())


class PortCodeResolver:
    """按 code / name_en / name_zh 匹配船公司返回的港口原始名称。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._by_code: dict[str, dict[str, str]] = {}
        self._by_en: dict[str, dict[str, str]] = {}
        self._by_zh: dict[str, dict[str, str]] = {}
        self._load(conn)

    def _load(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT code, name_zh, name_en
            FROM port_codes
            WHERE is_active = 1
            """
        ).fetchall()
        for row in rows:
            item = {
                "code": row["code"],
                "nameZh": row["name_zh"] or "",
                "nameEn": row["name_en"] or "",
            }
            code_key = (row["code"] or "").strip().upper()
            if code_key:
                self._by_code[code_key] = item
            en = (row["name_en"] or "").strip()
            if en:
                self._by_en[_norm_key(en)] = item
                self._by_en[en.strip().upper()] = item
            zh = (row["name_zh"] or "").strip()
            if zh:
                self._by_zh[zh] = item

    def resolve(self, carrier_port_name: str) -> dict[str, str] | None:
        raw = (carrier_port_name or "").strip()
        if not raw:
            return None
        if raw.upper() in self._by_code:
            return self._by_code[raw.upper()]
        if raw in self._by_zh:
            return self._by_zh[raw]
        key = _norm_key(raw)
        if key in self._by_en:
            return self._by_en[key]
        upper = raw.upper()
        if upper in self._by_en:
            return self._by_en[upper]
        return None

    def enrich_port_call(self, row: dict[str, Any]) -> dict[str, Any]:
        hit = self.resolve(str(row.get("portName") or ""))
        if not hit:
            return row
        return {
            **row,
            "portCode": hit["code"],
            "portCnname": hit["nameZh"],
            "portNameEn": hit["nameEn"],
        }
