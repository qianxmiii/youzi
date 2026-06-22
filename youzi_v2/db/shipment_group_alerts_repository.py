"""运单分组规则与提醒事件。"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Any

from .connection import Database
from .datetime_util import DATETIME_FMT, now_str
from .shipment_groups_table import GROUPS_TABLE, NOTIFICATIONS_TABLE, RULES_TABLE, TYPES_TABLE
from ..shipment_group_types import rule_applies_to_group_types, sort_group_types

RULE_TYPES = frozenset({"BATCH_DELIVERY_DEADLINE", "LAST_BATCH_ARRIVED_PAYMENT"})

_DEFAULT_RULES: tuple[tuple[str, int | None, int | None], ...] = (
    ("BATCH_DELIVERY_DEADLINE", 30, 7),
    ("LAST_BATCH_ARRIVED_PAYMENT", None, None),
)


def _notification_to_api(row: sqlite3.Row) -> dict[str, Any]:
    read_at = (row["read_at"] or "").strip()
    resolved_at = (row["resolved_at"] or "").strip()
    out: dict[str, Any] = {
        "id": row["id"],
        "groupId": row["group_id"],
        "ruleType": row["rule_type"],
        "severity": row["severity"],
        "title": row["title"],
        "message": row["message"],
        "shipmentNo": row["shipment_no"] or "",
        "eventKey": row["event_key"],
        "triggeredAt": row["triggered_at"],
        "readAt": read_at or None,
        "resolvedAt": resolved_at or None,
    }
    if "group_no" in row.keys():
        out["groupNo"] = row["group_no"] or ""
    if "group_name" in row.keys():
        out["groupName"] = row["group_name"] or ""
    return out


class ShipmentGroupAlertsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_group_types(self, group_id: str) -> list[str]:
        gid = group_id.strip()
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT group_type FROM {TYPES_TABLE}
                WHERE group_id = ?
                ORDER BY group_type
                """,
                (gid,),
            ).fetchall()
        if rows:
            return sort_group_types([str(r["group_type"]) for r in rows])
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT primary_type FROM {GROUPS_TABLE} WHERE id = ?",
                (gid,),
            ).fetchone()
        if not row:
            return ["MANUAL"]
        primary = (row["primary_type"] or "MANUAL").strip().upper() or "MANUAL"
        return [primary]

    def _resolve_group_types(
        self,
        group_id: str,
        group_types: list[str] | None = None,
    ) -> frozenset[str]:
        if group_types:
            return frozenset(sort_group_types(group_types))
        return frozenset(self.list_group_types(group_id))

    def ensure_default_rules(
        self,
        group_id: str,
        *,
        group_types: list[str] | None = None,
        group_type: str | None = None,
    ) -> None:
        gid = group_id.strip()
        if group_type and not group_types:
            types = frozenset([group_type.strip().upper()])
        else:
            types = self._resolve_group_types(gid, group_types)
        now = now_str()
        with self._database.lock:
            for rule_type, threshold, warning in _DEFAULT_RULES:
                enabled = 1 if rule_applies_to_group_types(rule_type, types) else 0
                existing = self._conn.execute(
                    f"SELECT id FROM {RULES_TABLE} WHERE group_id = ? AND rule_type = ?",
                    (gid, rule_type),
                ).fetchone()
                if existing:
                    self._conn.execute(
                        f"""
                        UPDATE {RULES_TABLE}
                        SET enabled = ?, updated_time = ?
                        WHERE group_id = ? AND rule_type = ?
                        """,
                        (enabled, now, gid, rule_type),
                    )
                    continue
                self._conn.execute(
                    f"""
                    INSERT INTO {RULES_TABLE} (
                        id, group_id, rule_type, enabled,
                        threshold_days, warning_days, trigger_status,
                        config_json, created_time, updated_time
                    ) VALUES (?, ?, ?, ?, ?, ?, '', '{{}}', ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        gid,
                        rule_type,
                        enabled,
                        threshold,
                        warning,
                        now,
                        now,
                    ),
                )
            self._conn.commit()

    def list_rules(self, group_id: str) -> list[dict[str, Any]]:
        gid = group_id.strip()
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {RULES_TABLE}
                WHERE group_id = ?
                ORDER BY rule_type
                """,
                (gid,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "groupId": r["group_id"],
                "ruleType": r["rule_type"],
                "enabled": bool(r["enabled"]),
                "thresholdDays": r["threshold_days"],
                "warningDays": r["warning_days"],
                "triggerStatus": r["trigger_status"] or "",
                "configJson": r["config_json"] or "{}",
                "createdTime": r["created_time"],
                "updatedTime": r["updated_time"],
            }
            for r in rows
        ]

    def get_rule(self, group_id: str, rule_type: str) -> dict[str, Any] | None:
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT * FROM {RULES_TABLE}
                WHERE group_id = ? AND rule_type = ?
                """,
                (group_id.strip(), rule_type.strip().upper()),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "groupId": row["group_id"],
            "ruleType": row["rule_type"],
            "enabled": bool(row["enabled"]),
            "thresholdDays": row["threshold_days"],
            "warningDays": row["warning_days"],
            "triggerStatus": row["trigger_status"] or "",
            "configJson": row["config_json"] or "{}",
        }

    def upsert_notification(
        self,
        *,
        group_id: str,
        rule_type: str,
        event_key: str,
        title: str,
        message: str,
        severity: str = "warning",
        shipment_no: str = "",
    ) -> bool:
        """写入提醒；event_key 已存在则跳过。返回是否新建。"""
        gid = group_id.strip()
        key = event_key.strip()
        now = now_str()
        with self._database.lock:
            existing = self._conn.execute(
                f"SELECT id FROM {NOTIFICATIONS_TABLE} WHERE event_key = ?",
                (key,),
            ).fetchone()
            if existing:
                return False
            self._conn.execute(
                f"""
                INSERT INTO {NOTIFICATIONS_TABLE} (
                    id, group_id, rule_type, severity, title, message,
                    shipment_no, event_key, triggered_at, read_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', '')
                """,
                (
                    str(uuid.uuid4()),
                    gid,
                    rule_type.strip().upper(),
                    severity,
                    title,
                    message,
                    (shipment_no or "").strip(),
                    key,
                    now,
                ),
            )
            self._conn.commit()
        return True

    def list_notifications(
        self,
        group_id: str,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        gid = group_id.strip()
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        conditions = ["group_id = ?"]
        params: list[Any] = [gid]
        if unread_only:
            conditions.append("(read_at IS NULL OR TRIM(read_at) = '')")
        where = f"WHERE {' AND '.join(conditions)}"
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {NOTIFICATIONS_TABLE} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT * FROM {NOTIFICATIONS_TABLE}
                {where}
                ORDER BY datetime(triggered_at) DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return {
            "items": [_notification_to_api(r) for r in rows],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    def list_unread_notifications(self, *, limit: int = 20) -> list[dict[str, Any]]:
        lim = max(1, min(limit, 50))
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT n.*, g.group_no, g.group_name
                FROM {NOTIFICATIONS_TABLE} n
                INNER JOIN {GROUPS_TABLE} g ON g.id = n.group_id
                WHERE n.read_at IS NULL OR TRIM(n.read_at) = ''
                ORDER BY datetime(n.triggered_at) DESC
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
        return [_notification_to_api(r) for r in rows]

    def count_unread(self, group_id: str | None = None) -> int:
        with self._database.lock:
            if group_id:
                row = self._conn.execute(
                    f"""
                    SELECT COUNT(*) AS c FROM {NOTIFICATIONS_TABLE}
                    WHERE group_id = ?
                      AND (read_at IS NULL OR TRIM(read_at) = '')
                    """,
                    (group_id.strip(),),
                ).fetchone()
            else:
                row = self._conn.execute(
                    f"""
                    SELECT COUNT(*) AS c FROM {NOTIFICATIONS_TABLE}
                    WHERE read_at IS NULL OR TRIM(read_at) = ''
                    """
                ).fetchone()
        return int(row["c"] or 0)

    def mark_read(self, notification_id: str) -> bool:
        nid = notification_id.strip()
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {NOTIFICATIONS_TABLE}
                SET read_at = ?
                WHERE id = ? AND (read_at IS NULL OR TRIM(read_at) = '')
                """,
                (now, nid),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def mark_resolved(self, notification_id: str) -> bool:
        nid = notification_id.strip()
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {NOTIFICATIONS_TABLE}
                SET resolved_at = ?,
                    read_at = CASE
                        WHEN read_at IS NULL OR TRIM(read_at) = '' THEN ?
                        ELSE read_at
                    END
                WHERE id = ? AND (resolved_at IS NULL OR TRIM(resolved_at) = '')
                """,
                (now, now, nid),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def mark_all_read(self, group_id: str | None = None) -> int:
        now = now_str()
        with self._database.lock:
            if group_id:
                cur = self._conn.execute(
                    f"""
                    UPDATE {NOTIFICATIONS_TABLE}
                    SET read_at = ?
                    WHERE group_id = ?
                      AND (read_at IS NULL OR TRIM(read_at) = '')
                    """,
                    (now, group_id.strip()),
                )
            else:
                cur = self._conn.execute(
                    f"""
                    UPDATE {NOTIFICATIONS_TABLE}
                    SET read_at = ?
                    WHERE read_at IS NULL OR TRIM(read_at) = ''
                    """,
                    (now,),
                )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def delete_for_group(self, group_id: str) -> None:
        gid = group_id.strip()
        with self._database.lock:
            self._conn.execute(
                f"DELETE FROM {NOTIFICATIONS_TABLE} WHERE group_id = ?",
                (gid,),
            )
            self._conn.execute(
                f"DELETE FROM {RULES_TABLE} WHERE group_id = ?",
                (gid,),
            )
            self._conn.commit()

    def list_group_ids(self, *, group_id: str | None = None) -> list[str]:
        with self._database.lock:
            if group_id:
                row = self._conn.execute(
                    f"SELECT id FROM {GROUPS_TABLE} WHERE id = ?",
                    (group_id.strip(),),
                ).fetchone()
                return [str(row["id"])] if row else []
            rows = self._conn.execute(f"SELECT id FROM {GROUPS_TABLE}").fetchall()
        return [str(r["id"]) for r in rows]

    def list_group_ids_for_shipments(self, shipment_ids: list[str]) -> list[str]:
        ids = [s.strip() for s in shipment_ids if s and s.strip()]
        if not ids:
            return []
        placeholders = ", ".join("?" * len(ids))
        from .shipment_groups_table import MEMBERS_TABLE

        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT DISTINCT group_id FROM {MEMBERS_TABLE}
                WHERE shipment_id IN ({placeholders})
                """,
                ids,
            ).fetchall()
        return [str(r["group_id"]) for r in rows]

    @staticmethod
    def parse_dt(raw: str | None) -> datetime | None:
        from .datetime_util import normalize_tracking_time

        text = normalize_tracking_time(raw)
        if not text:
            return None
        try:
            return datetime.strptime(text, DATETIME_FMT)
        except ValueError:
            return None
