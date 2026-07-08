"""渠道运输时效规则 CRUD。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .channel_sla_rules_table import TABLE_NAME
from .connection import Database
from .datetime_util import now_str


def _rule_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "channelCode": row["channel_code"],
        "carrierCode": row["carrier_code"] or "",
        "startField": row["start_field"] or "ATD",
        "estimatedDays": int(row["estimated_days"] or 0),
        "warningDays": int(row["warning_days"] or 3),
        "severeOverdueDays": int(row["severe_overdue_days"] or 7),
        "enabled": bool(row["enabled"]),
        "note": row["note"] or "",
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


class ChannelSlaRulesRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_by_channel(self, channel_code: str) -> list[dict[str, Any]]:
        code = channel_code.strip()
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE channel_code = ?
                ORDER BY carrier_code, start_field
                """,
                (code,),
            ).fetchall()
        return [_rule_to_api(r) for r in rows]

    def list_enabled_grouped(self) -> dict[str, list[dict[str, Any]]]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE enabled = 1
                ORDER BY channel_code, carrier_code, start_field
                """
            ).fetchall()
        out: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            api = _rule_to_api(row)
            out.setdefault(api["channelCode"], []).append(api)
        return out

    def upsert_rule(
        self,
        *,
        channel_code: str,
        estimated_days: int,
        carrier_code: str = "",
        start_field: str = "ATD",
        warning_days: int = 3,
        severe_overdue_days: int = 7,
        enabled: bool = True,
        note: str = "",
        rule_id: str | None = None,
    ) -> dict[str, Any]:
        channel = channel_code.strip()
        if not channel:
            raise ValueError("渠道不能为空")
        if estimated_days <= 0:
            raise ValueError("预估天数必须大于 0")
        carrier = (carrier_code or "").strip()
        start = (start_field or "ATD").strip().upper()
        now = now_str()
        with self._database.lock:
            if rule_id:
                cur = self._conn.execute(
                    f"""
                    UPDATE {TABLE_NAME}
                    SET estimated_days = ?, warning_days = ?, severe_overdue_days = ?,
                        enabled = ?, note = ?, updated_time = ?
                    WHERE id = ? AND channel_code = ?
                    """,
                    (
                        int(estimated_days),
                        int(warning_days),
                        int(severe_overdue_days),
                        1 if enabled else 0,
                        (note or "").strip(),
                        now,
                        rule_id.strip(),
                        channel,
                    ),
                )
                if cur.rowcount == 0:
                    raise KeyError("规则不存在")
            else:
                existing = self._conn.execute(
                    f"""
                    SELECT id FROM {TABLE_NAME}
                    WHERE channel_code = ? AND carrier_code = ? AND start_field = ?
                    """,
                    (channel, carrier, start),
                ).fetchone()
                if existing:
                    self._conn.execute(
                        f"""
                        UPDATE {TABLE_NAME}
                        SET estimated_days = ?, warning_days = ?, severe_overdue_days = ?,
                            enabled = ?, note = ?, updated_time = ?
                        WHERE id = ?
                        """,
                        (
                            int(estimated_days),
                            int(warning_days),
                            int(severe_overdue_days),
                            1 if enabled else 0,
                            (note or "").strip(),
                            now,
                            existing["id"],
                        ),
                    )
                else:
                    self._conn.execute(
                        f"""
                        INSERT INTO {TABLE_NAME} (
                            id, channel_code, carrier_code, start_field,
                            estimated_days, warning_days, severe_overdue_days,
                            enabled, note, created_time, updated_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            channel,
                            carrier,
                            start,
                            int(estimated_days),
                            int(warning_days),
                            int(severe_overdue_days),
                            1 if enabled else 0,
                            (note or "").strip(),
                            now,
                            now,
                        ),
                    )
            self._conn.commit()
        rules = self.list_by_channel(channel)
        if rule_id:
            for r in rules:
                if r["id"] == rule_id:
                    return r
        default = [r for r in rules if not r["carrierCode"] and r["startField"] == start]
        return default[0] if default else rules[0]

    def delete_rule(self, rule_id: str) -> bool:
        rid = rule_id.strip()
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE id = ?",
                (rid,),
            )
            self._conn.commit()
            return cur.rowcount > 0
