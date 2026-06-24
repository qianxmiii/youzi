"""运单分组规则与提醒事件。"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from .connection import Database
from .datetime_util import DATETIME_FMT, now_str
from .shipment_groups_table import GROUPS_TABLE, NOTIFICATIONS_TABLE, RULES_TABLE
from ..shipment_group_rules import (
    DEFAULT_RULE_THRESHOLDS,
    RULE_TYPES,
    normalize_rule_type,
    validate_rule_payload,
)

RULE_TYPE_LEGACY_GROUP_ARRIVED = "LAST_BATCH_ARRIVED_PAYMENT"


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
    if "customer" in row.keys():
        out["customer"] = (row["customer"] or "").strip() or None
    return out


def _rule_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "groupId": row["group_id"],
        "ruleType": row["rule_type"],
        "enabled": bool(row["enabled"]),
        "thresholdDays": row["threshold_days"],
        "warningDays": row["warning_days"],
        "triggerStatus": row["trigger_status"] or "",
        "configJson": row["config_json"] or "{}",
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


class ShipmentGroupAlertsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

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
        return [_rule_to_api(r) for r in rows]

    def get_rule(self, group_id: str, rule_type: str) -> dict[str, Any] | None:
        rt = normalize_rule_type(rule_type)
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT * FROM {RULES_TABLE}
                WHERE group_id = ? AND rule_type = ?
                """,
                (group_id.strip(), rt),
            ).fetchone()
        if not row:
            legacy = (
                RULE_TYPE_LEGACY_GROUP_ARRIVED
                if rt == "GROUP_ARRIVED_PAYMENT"
                else None
            )
            if legacy:
                with self._database.lock:
                    row = self._conn.execute(
                        f"""
                        SELECT * FROM {RULES_TABLE}
                        WHERE group_id = ? AND rule_type = ?
                        """,
                        (group_id.strip(), legacy),
                    ).fetchone()
        if not row:
            return None
        return _rule_to_api(row)

    def replace_rules(self, group_id: str, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        gid = group_id.strip()
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for raw in rules:
            rt = normalize_rule_type(str(raw.get("ruleType") or raw.get("rule_type") or ""))
            if rt in seen:
                raise ValueError(f"规则重复：{rt}")
            seen.add(rt)
            normalized.append(validate_rule_payload(rt, raw))

        now = now_str()
        with self._database.lock:
            self._conn.execute(f"DELETE FROM {RULES_TABLE} WHERE group_id = ?", (gid,))
            for rule in normalized:
                self._conn.execute(
                    f"""
                    INSERT INTO {RULES_TABLE} (
                        id, group_id, rule_type, enabled,
                        threshold_days, warning_days, trigger_status,
                        config_json, created_time, updated_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        gid,
                        rule["ruleType"],
                        1 if rule["enabled"] else 0,
                        rule["thresholdDays"],
                        rule["warningDays"],
                        rule["triggerStatus"],
                        rule["configJson"],
                        now,
                        now,
                    ),
                )
            self._conn.commit()
        return self.list_rules(gid)

    def patch_rule(
        self,
        group_id: str,
        rule_type: str,
        patch: dict[str, Any],
    ) -> dict[str, Any] | None:
        gid = group_id.strip()
        rt = normalize_rule_type(rule_type)
        existing = self.get_rule(gid, rt)
        merged: dict[str, Any] = {
            "ruleType": rt,
            "enabled": existing["enabled"] if existing else True,
            "thresholdDays": existing["thresholdDays"] if existing else None,
            "warningDays": existing["warningDays"] if existing else None,
            "triggerStatus": existing["triggerStatus"] if existing else "",
            "configJson": existing["configJson"] if existing else "{}",
        }
        if "enabled" in patch:
            merged["enabled"] = bool(patch["enabled"])
        if "thresholdDays" in patch or "threshold_days" in patch:
            merged["thresholdDays"] = patch.get("thresholdDays", patch.get("threshold_days"))
        if "warningDays" in patch or "warning_days" in patch:
            merged["warningDays"] = patch.get("warningDays", patch.get("warning_days"))
        if "triggerStatus" in patch or "trigger_status" in patch:
            merged["triggerStatus"] = patch.get("triggerStatus", patch.get("trigger_status"))
        if "configJson" in patch or "config_json" in patch:
            merged["configJson"] = patch.get("configJson", patch.get("config_json"))

        rule = validate_rule_payload(rt, merged)
        now = now_str()
        with self._database.lock:
            if existing:
                self._conn.execute(
                    f"""
                    UPDATE {RULES_TABLE}
                    SET enabled = ?, threshold_days = ?, warning_days = ?,
                        trigger_status = ?, config_json = ?, updated_time = ?
                    WHERE group_id = ? AND rule_type = ?
                    """,
                    (
                        1 if rule["enabled"] else 0,
                        rule["thresholdDays"],
                        rule["warningDays"],
                        rule["triggerStatus"],
                        rule["configJson"],
                        now,
                        gid,
                        rt,
                    ),
                )
            else:
                self._conn.execute(
                    f"""
                    INSERT INTO {RULES_TABLE} (
                        id, group_id, rule_type, enabled,
                        threshold_days, warning_days, trigger_status,
                        config_json, created_time, updated_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        gid,
                        rt,
                        1 if rule["enabled"] else 0,
                        rule["thresholdDays"],
                        rule["warningDays"],
                        rule["triggerStatus"],
                        rule["configJson"],
                        now,
                        now,
                    ),
                )
            self._conn.commit()
        return self.get_rule(gid, rt)

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
                    normalize_rule_type(rule_type),
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
        conditions = ["n.group_id = ?"]
        params: list[Any] = [gid]
        if unread_only:
            conditions.append("(n.read_at IS NULL OR TRIM(n.read_at) = '')")
        where = f"WHERE {' AND '.join(conditions)}"
        with self._database.lock:
            total = self._conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {NOTIFICATIONS_TABLE} n
                {where}
                """,
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT n.*, g.group_no, g.group_name, g.customer
                FROM {NOTIFICATIONS_TABLE} n
                INNER JOIN {GROUPS_TABLE} g ON g.id = n.group_id
                {where}
                ORDER BY datetime(n.triggered_at) DESC
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
                SELECT n.*, g.group_no, g.group_name, g.customer
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

    def list_group_ids(
        self,
        *,
        group_id: str | None = None,
        rule_type: str | None = None,
        has_rule: bool | None = None,
    ) -> list[str]:
        with self._database.lock:
            if group_id:
                row = self._conn.execute(
                    f"SELECT id FROM {GROUPS_TABLE} WHERE id = ?",
                    (group_id.strip(),),
                ).fetchone()
                return [str(row["id"])] if row else []
            if rule_type and rule_type.strip():
                rt = normalize_rule_type(rule_type)
                rows = self._conn.execute(
                    f"""
                    SELECT DISTINCT group_id FROM {RULES_TABLE}
                    WHERE rule_type = ? AND enabled = 1
                    """,
                    (rt,),
                ).fetchall()
                return [str(r["group_id"]) for r in rows]
            if has_rule is True:
                rows = self._conn.execute(
                    f"""
                    SELECT DISTINCT group_id FROM {RULES_TABLE}
                    WHERE enabled = 1
                    """
                ).fetchall()
                return [str(r["group_id"]) for r in rows]
            if has_rule is False:
                rows = self._conn.execute(
                    f"""
                    SELECT g.id FROM {GROUPS_TABLE} g
                    WHERE NOT EXISTS (
                      SELECT 1 FROM {RULES_TABLE} r
                      WHERE r.group_id = g.id AND r.enabled = 1
                    )
                    """
                ).fetchall()
                return [str(r["id"]) for r in rows]
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

    @staticmethod
    def default_rules_payload() -> list[dict[str, Any]]:
        return [
            {
                "ruleType": rt,
                "enabled": False,
                "thresholdDays": DEFAULT_RULE_THRESHOLDS[rt][0],
                "warningDays": DEFAULT_RULE_THRESHOLDS[rt][1],
            }
            for rt in sorted(RULE_TYPES)
        ]
