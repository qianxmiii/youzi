"""运输时效预警 CRUD 与列表查询。"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .shipment_sla import (
    ACTIVE_STATUSES,
    RISK_OVERDUE,
    RISK_SEVERE_OVERDUE,
    STATUS_ACKNOWLEDGED,
    STATUS_CONVERTED,
    STATUS_IGNORED,
    STATUS_OPEN,
    STATUS_RESOLVED,
    compute_days_in_transit,
    days_until_due,
    is_delivered,
    match_channel_rule,
    parse_date,
    risk_to_severity,
    sla_excluded_channels_in_sql,
    sla_excluded_channels_params,
    sla_excluded_channels_sql,
)
from .exception_duration import duration_seconds, format_duration
from .shipment_sla_alerts_table import TABLE_NAME
from .shipment_sla_alert_followups_table import TABLE_NAME as FOLLOWUPS_TABLE
from .channel_sla_rules_table import TABLE_NAME as RULES_TABLE
from .shipment_exception_events_table import TABLE_NAME as EXCEPTION_EVENTS_TABLE
from .shipments_table import TABLE_NAME as SHIPMENTS_TABLE

EXCEPTION_CODES_TABLE = "shipment_exception_codes"
CARRIER_CODES_TABLE = "carrier_codes"

RESOLVE_ON_DELIVERY_STATUSES = ("open", "acknowledged", STATUS_CONVERTED)

_FOLLOW_UP_STATS_SQL = f"""
(SELECT COUNT(*) FROM {FOLLOWUPS_TABLE} fu WHERE fu.alert_id = a.id) AS follow_up_count,
(SELECT MAX(fu.followed_time) FROM {FOLLOWUPS_TABLE} fu WHERE fu.alert_id = a.id) AS last_follow_up_time
"""

_LAST_CLOSED_EXCEPTION_JOIN = f"""
LEFT JOIN (
    SELECT shipment_no, opened_time, closed_time
    FROM (
        SELECT shipment_no, opened_time, closed_time,
               ROW_NUMBER() OVER (
                   PARTITION BY shipment_no
                   ORDER BY datetime(closed_time) DESC, datetime(updated_time) DESC
               ) AS rn
        FROM {EXCEPTION_EVENTS_TABLE}
        WHERE closed_time IS NOT NULL AND TRIM(closed_time) != ''
    )
    WHERE rn = 1
) last_closed_exc ON last_closed_exc.shipment_no = s.shipment_no
"""


def _follow_up_fields(row: sqlite3.Row, *, today: date | None = None) -> dict[str, Any]:
    count = int(row["follow_up_count"] or 0) if "follow_up_count" in row.keys() else 0
    last_raw = ""
    if "last_follow_up_time" in row.keys() and row["last_follow_up_time"]:
        last_raw = (row["last_follow_up_time"] or "").strip()
    ack_raw = (row["acknowledged_time"] or "").strip() if "acknowledged_time" in row.keys() else ""
    if count <= 0 and ack_raw:
        count = 1
        last_raw = ack_raw or last_raw
    last_day = parse_date(last_raw)
    end = today or date.today()
    days_ago = max(0, (end - last_day).days) if last_day else None
    return {
        "followUpCount": count,
        "lastFollowUpTime": last_raw or None,
        "lastFollowUpDaysAgo": days_ago,
    }


def _resolve_estimated_days(
    row: sqlite3.Row,
    *,
    rules_by_channel: dict[str, list[dict[str, Any]]] | None = None,
) -> int | None:
    if "rule_estimated_days" in row.keys() and row["rule_estimated_days"] is not None:
        return int(row["rule_estimated_days"])
    if not rules_by_channel:
        return None
    channel_code = (row["channel_code"] or "").strip()
    if not channel_code:
        return None
    carrier_code = ""
    if "ship_carrier_code" in row.keys() and (row["ship_carrier_code"] or "").strip():
        carrier_code = (row["ship_carrier_code"] or "").strip()
    elif "carrier_code" in row.keys() and (row["carrier_code"] or "").strip():
        carrier_code = (row["carrier_code"] or "").strip()
    rule = match_channel_rule(
        rules_by_channel,
        channel_code=channel_code,
        carrier_code=carrier_code,
    )
    if not rule:
        return None
    estimated = int(rule.get("estimatedDays") or 0)
    return estimated if estimated > 0 else None


def _exception_duration_fields(row: sqlite3.Row) -> dict[str, Any]:
    code = (row["exception_code"] or "").strip() if "exception_code" in row.keys() else ""
    opened = (
        (row["exception_opened_time"] or "").strip()
        if "exception_opened_time" in row.keys()
        else ""
    )
    if code and opened:
        secs = duration_seconds(opened, None)
        return {
            "exceptionDurationSeconds": secs,
            "exceptionDurationLabel": format_duration(secs, opened_time=opened),
        }
    closed_opened = (
        (row["last_exc_opened_time"] or "").strip()
        if "last_exc_opened_time" in row.keys()
        else ""
    )
    closed_at = (
        (row["last_exc_closed_time"] or "").strip()
        if "last_exc_closed_time" in row.keys()
        else ""
    )
    if closed_opened and closed_at:
        secs = duration_seconds(closed_opened, closed_at)
        return {
            "exceptionDurationSeconds": secs,
            "exceptionDurationLabel": format_duration(
                secs,
                opened_time=closed_opened,
                closed_time=closed_at,
            ),
        }
    return {"exceptionDurationSeconds": None, "exceptionDurationLabel": None}


def _exception_calendar_days(row: sqlite3.Row, *, today: date | None = None) -> int:
    """异常占用日历天数，与 exceptionDurationLabel 口径一致。"""
    check_day = today or date.today()
    code = (row["exception_code"] or "").strip() if "exception_code" in row.keys() else ""
    opened = (
        (row["exception_opened_time"] or "").strip()
        if "exception_opened_time" in row.keys()
        else ""
    )
    if code and opened:
        start = parse_date(opened)
        if start is None:
            return 0
        return max(0, (check_day - start).days)
    closed_opened = (
        (row["last_exc_opened_time"] or "").strip()
        if "last_exc_opened_time" in row.keys()
        else ""
    )
    closed_at = (
        (row["last_exc_closed_time"] or "").strip()
        if "last_exc_closed_time" in row.keys()
        else ""
    )
    if closed_opened and closed_at:
        start = parse_date(closed_opened)
        end = parse_date(closed_at)
        if start is None or end is None:
            return 0
        return max(0, (end - start).days)
    return 0


def _alert_to_api(
    row: sqlite3.Row,
    *,
    rules_by_channel: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    due_day = parse_date(row["due_date"])
    today = date.today()
    days_delta = days_until_due(today, due_day) if due_day else None
    out: dict[str, Any] = {
        "id": row["id"],
        "shipmentId": row["shipment_id"],
        "shipmentNo": row["shipment_no"],
        "alertType": row["alert_type"],
        "riskLevel": row["risk_level"],
        "status": row["status"],
        "severity": row["severity"],
        "ruleId": row["rule_id"] or "",
        "ruleScope": row["rule_scope"] or "",
        "channelCode": row["channel_code"] or "",
        "carrierCode": (
            (row["ship_carrier_code"] or "").strip()
            if "ship_carrier_code" in row.keys() and (row["ship_carrier_code"] or "").strip()
            else (row["carrier_code"] or "").strip()
        ),
        "startField": row["start_field"] or "",
        "startTime": row["start_time"] or "",
        "dueDate": row["due_date"],
        "warningDate": row["warning_date"] or "",
        "convertedExceptionCode": row["converted_exception_code"] or "",
        "convertedEventId": row["converted_event_id"] or "",
        "acknowledgedTime": row["acknowledged_time"] or None,
        "resolvedTime": row["resolved_time"] or None,
        "ignoredTime": row["ignored_time"] or None,
        "owner": row["owner"] or "",
        "note": row["note"] or "",
        "eventKey": row["event_key"],
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
        "daysUntilDue": days_delta,
        "overdueDays": abs(days_delta) if days_delta is not None and days_delta < 0 else 0,
    }
    transit_start = ""
    if "atd" in row.keys() and (row["atd"] or "").strip():
        transit_start = (row["atd"] or "").strip()
    elif (row["start_field"] or "").strip().upper() == "ATD":
        transit_start = (row["start_time"] or "").strip()
    else:
        transit_start = (row["start_time"] or "").strip()
    delivered_time = ""
    if "delivered_time" in row.keys():
        delivered_time = (row["delivered_time"] or "").strip()
    status_code = (row["status_code"] or "").strip() if "status_code" in row.keys() else ""
    if is_delivered({"delivered_time": delivered_time, "status_code": status_code}):
        out["daysInTransit"] = compute_days_in_transit(
            transit_start,
            delivered_time=delivered_time or None,
        )
    else:
        out["daysInTransit"] = compute_days_in_transit(transit_start, today=today)
    out["estimatedDays"] = _resolve_estimated_days(row, rules_by_channel=rules_by_channel)
    out.update(_exception_duration_fields(row))
    total_days = out.get("daysInTransit")
    exc_days = _exception_calendar_days(row, today=today)
    out["totalDaysInTransit"] = total_days
    if total_days is None:
        out["netDaysInTransit"] = None
    else:
        out["netDaysInTransit"] = max(0, int(total_days) - exc_days)
    for key in (
        "customer",
        "destinationPort",
        "atd",
        "ata",
        "expectedDeliveryTime",
        "warehouseEntryTime",
        "deliveredTime",
        "exceptionCode",
        "exceptionNameZh",
        "latestTrackingDesc",
        "latestTrackingTime",
        "channelNameZh",
        "carrierNameZh",
    ):
        col = {
            "customer": "customer",
            "destinationPort": "destination_port_code",
            "atd": "atd",
            "ata": "ata",
            "warehouseEntryTime": "warehouse_entry_time",
            "expectedDeliveryTime": "expected_delivery_time",
            "deliveredTime": "delivered_time",
            "exceptionCode": "exception_code",
            "exceptionNameZh": "exception_name_zh",
            "latestTrackingDesc": "latest_tracking_desc",
            "latestTrackingTime": "latest_tracking_time",
            "channelNameZh": "channel_name_zh",
            "carrierNameZh": "carrier_name_zh",
        }[key]
        if col in row.keys():
            val = row[col]
            out[key] = (val or "").strip() if isinstance(val, str) else val
    out.update(_follow_up_fields(row, today=today))
    return out


class ShipmentSlaAlertsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _load_channel_rules_grouped(self) -> dict[str, list[dict[str, Any]]]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT id, channel_code, carrier_code, start_field, estimated_days,
                       warning_days, severe_overdue_days, enabled, note, created_time, updated_time
                FROM {RULES_TABLE}
                WHERE enabled = 1
                ORDER BY channel_code, carrier_code, start_field
                """
            ).fetchall()
        out: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            channel = (row["channel_code"] or "").strip()
            if not channel:
                continue
            item = {
                "id": row["id"],
                "channelCode": channel,
                "carrierCode": (row["carrier_code"] or "").strip(),
                "startField": row["start_field"] or "ATD",
                "estimatedDays": int(row["estimated_days"] or 0),
                "warningDays": int(row["warning_days"] or 3),
                "severeOverdueDays": int(row["severe_overdue_days"] or 7),
                "enabled": bool(row["enabled"]),
            }
            out.setdefault(channel, []).append(item)
        return out

    def list_undelivered_shipments(self) -> list[dict[str, Any]]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT id, shipment_no, channel_code, carrier_code, customer,
                       destination_port_code, atd, etd, ata, warehouse_entry_time,
                       expected_delivery_time, delivered_time,
                       status_code, exception_code, latest_tracking_desc, latest_tracking_time
                FROM {SHIPMENTS_TABLE}
                WHERE (delivered_time IS NULL OR TRIM(delivered_time) = '')
                  AND UPPER(COALESCE(status_code, '')) != 'DELIVERED'
                  AND {sla_excluded_channels_sql("channel_code")}
                ORDER BY shipment_no
                """,
                sla_excluded_channels_params(),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_by_event_key(self, event_key: str) -> dict[str, Any] | None:
        key = event_key.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE event_key = ?",
                (key,),
            ).fetchone()
        return _alert_to_api(row) if row else None

    def find_active_for_shipment(self, shipment_id: str) -> list[dict[str, Any]]:
        sid = shipment_id.strip()
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE shipment_id = ?
                  AND status IN ('open', 'acknowledged')
                ORDER BY datetime(created_time) DESC
                """,
                (sid,),
            ).fetchall()
        return [_alert_to_api(r) for r in rows]

    def upsert_alert(
        self,
        *,
        shipment_id: str,
        shipment_no: str,
        risk_level: str,
        event_key: str,
        due_date: str,
        warning_date: str,
        rule_id: str,
        rule_scope: str,
        channel_code: str,
        carrier_code: str,
        start_field: str,
        start_time: str,
        alert_type: str = "DELIVERY_TIME",
    ) -> bool:
        """新建或更新 open/acknowledged 预警；返回是否新建。"""
        key = event_key.strip()
        now = now_str()
        severity = risk_to_severity(risk_level)
        alert = (alert_type or "DELIVERY_TIME").strip()
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT id, status FROM {TABLE_NAME} WHERE event_key = ?",
                (key,),
            ).fetchone()
            if row:
                status = (row["status"] or "").strip()
                if status in ACTIVE_STATUSES:
                    self._conn.execute(
                        f"""
                        UPDATE {TABLE_NAME}
                        SET risk_level = ?, severity = ?, due_date = ?, warning_date = ?,
                            start_field = ?, start_time = ?, rule_scope = ?, rule_id = ?,
                            channel_code = ?, carrier_code = ?, updated_time = ?
                        WHERE id = ?
                        """,
                        (
                            risk_level,
                            severity,
                            due_date,
                            warning_date,
                            start_field,
                            start_time,
                            rule_scope,
                            rule_id,
                            channel_code,
                            carrier_code,
                            now,
                            row["id"],
                        ),
                    )
                    self._conn.commit()
                return False

            self._conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                    rule_id, rule_scope, channel_code, carrier_code, start_field, start_time,
                    due_date, warning_date, event_key, created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    shipment_id.strip(),
                    shipment_no.strip(),
                    alert,
                    risk_level,
                    STATUS_OPEN,
                    severity,
                    rule_id,
                    rule_scope,
                    channel_code,
                    carrier_code,
                    start_field,
                    start_time,
                    due_date,
                    warning_date,
                    key,
                    now,
                    now,
                ),
            )
            self._conn.commit()
        return True

    def resolve_open_for_shipment(
        self,
        shipment_id: str,
        *,
        alert_type: str | None = None,
    ) -> int:
        """签收或兜底清理：关闭 open / acknowledged / converted 预警。"""
        sid = shipment_id.strip()
        now = now_str()
        placeholders = ",".join("?" for _ in RESOLVE_ON_DELIVERY_STATUSES)
        type_clause = ""
        type_params: list[Any] = []
        if alert_type:
            type_clause = " AND alert_type = ?"
            type_params.append(alert_type.strip())
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET status = ?, resolved_time = ?, updated_time = ?
                WHERE shipment_id = ?
                  AND status IN ({placeholders}){type_clause}
                """,
                (STATUS_RESOLVED, now, now, sid, *RESOLVE_ON_DELIVERY_STATUSES, *type_params),
            )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def resolve_open_for_shipment_ids(self, shipment_ids: list[str]) -> int:
        ids = [i.strip() for i in shipment_ids if i and i.strip()]
        if not ids:
            return 0
        now = now_str()
        id_placeholders = ",".join("?" for _ in ids)
        status_placeholders = ",".join("?" for _ in RESOLVE_ON_DELIVERY_STATUSES)
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET status = ?, resolved_time = ?, updated_time = ?
                WHERE shipment_id IN ({id_placeholders})
                  AND status IN ({status_placeholders})
                """,
                (STATUS_RESOLVED, now, now, *ids, *RESOLVE_ON_DELIVERY_STATUSES),
            )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def resolve_delivered_stale_alerts(self) -> int:
        """扫描兜底：已签收运单上仍挂起的时效预警批量 resolved。"""
        now = now_str()
        status_placeholders = ",".join("?" for _ in RESOLVE_ON_DELIVERY_STATUSES)
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET status = ?, resolved_time = ?, updated_time = ?
                WHERE status IN ({status_placeholders})
                  AND shipment_id IN (
                    SELECT id FROM {SHIPMENTS_TABLE}
                    WHERE (delivered_time IS NOT NULL AND TRIM(delivered_time) != '')
                       OR UPPER(COALESCE(status_code, '')) = 'DELIVERED'
                  )
                """,
                (STATUS_RESOLVED, now, now, *RESOLVE_ON_DELIVERY_STATUSES),
            )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def resolve_excluded_channel_alerts(self) -> int:
        """关闭排除渠道运单上仍挂起的时效预警。"""
        now = now_str()
        status_placeholders = ",".join("?" for _ in RESOLVE_ON_DELIVERY_STATUSES)
        excl = sla_excluded_channels_params()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET status = ?, resolved_time = ?, updated_time = ?
                WHERE status IN ({status_placeholders})
                  AND shipment_id IN (
                    SELECT id FROM {SHIPMENTS_TABLE}
                    WHERE {sla_excluded_channels_in_sql("channel_code")}
                  )
                """,
                (STATUS_RESOLVED, now, now, *RESOLVE_ON_DELIVERY_STATUSES, *excl),
            )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def list_alerts(
        self,
        *,
        scope: str = "todo",
        risk_level: str | None = None,
        alert_type: str | None = None,
        status: str | None = None,
        has_exception: bool | None = None,
        exception_code: str | None = None,
        channel_code: str | None = None,
        carrier_code: str | None = None,
        customer: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        conditions = ["1=1"]
        params: list[Any] = list(sla_excluded_channels_params())
        conditions.append(sla_excluded_channels_sql("s.channel_code"))

        if (scope or "todo").strip().lower() != "all":
            conditions.append("a.status IN (?, ?)")
            params.extend([STATUS_OPEN, STATUS_ACKNOWLEDGED])
            conditions.append(
                "(s.delivered_time IS NULL OR TRIM(s.delivered_time) = '') "
                "AND UPPER(COALESCE(s.status_code, '')) != 'DELIVERED'"
            )
        if risk_level:
            conditions.append("a.risk_level = ?")
            params.append(risk_level.strip())
        if alert_type:
            conditions.append("a.alert_type = ?")
            params.append(alert_type.strip())
        if status:
            conditions.append("a.status = ?")
            params.append(status.strip())
        if channel_code:
            conditions.append("a.channel_code = ?")
            params.append(channel_code.strip())
        if carrier_code:
            conditions.append("s.carrier_code = ?")
            params.append(carrier_code.strip())
        if customer:
            conditions.append("TRIM(s.customer) = ? COLLATE NOCASE")
            params.append(customer.strip())
        if has_exception is True:
            conditions.append("s.exception_code IS NOT NULL AND TRIM(s.exception_code) != ''")
        elif has_exception is False:
            conditions.append("(s.exception_code IS NULL OR TRIM(s.exception_code) = '')")
        if exception_code:
            conditions.append("s.exception_code = ?")
            params.append(exception_code.strip().upper())
        if search:
            q = f"%{search.strip()}%"
            conditions.append("(a.shipment_no LIKE ? OR s.customer LIKE ?)")
            params.extend([q, q])

        where = " AND ".join(conditions)
        with self._database.lock:
            total = self._conn.execute(
                f"""
                SELECT COUNT(*) AS c
                FROM {TABLE_NAME} a
                INNER JOIN {SHIPMENTS_TABLE} s ON s.id = a.shipment_id
                WHERE {where}
                """,
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT a.*, s.customer, s.destination_port_code, s.atd, s.ata, s.warehouse_entry_time,
                       s.expected_delivery_time,
                       s.delivered_time, s.status_code, s.exception_code, s.exception_opened_time,
                       s.latest_tracking_desc,
                       s.latest_tracking_time, s.carrier_code AS ship_carrier_code,
                       cc.name_zh AS channel_name_zh,
                       COALESCE(NULLIF(TRIM(crc.name_zh), ''), NULLIF(TRIM(crc_by_id.name_zh), ''))
                           AS carrier_name_zh,
                       COALESCE(ec.name_zh, s.exception_code) AS exception_name_zh,
                       last_closed_exc.opened_time AS last_exc_opened_time,
                       last_closed_exc.closed_time AS last_exc_closed_time,
                       csr.estimated_days AS rule_estimated_days,
                       {_FOLLOW_UP_STATS_SQL}
                FROM {TABLE_NAME} a
                INNER JOIN {SHIPMENTS_TABLE} s ON s.id = a.shipment_id
                LEFT JOIN channel_codes cc ON cc.code = a.channel_code
                LEFT JOIN {CARRIER_CODES_TABLE} crc ON crc.code = s.carrier_code
                LEFT JOIN {CARRIER_CODES_TABLE} crc_by_id ON crc.code IS NULL
                    AND TRIM(COALESCE(s.carrier_code, '')) != ''
                    AND s.carrier_code = crc_by_id.carrier_id
                LEFT JOIN {EXCEPTION_CODES_TABLE} ec ON ec.code = s.exception_code
                {_LAST_CLOSED_EXCEPTION_JOIN}
                LEFT JOIN {RULES_TABLE} csr ON csr.id = a.rule_id
                WHERE {where}
                ORDER BY
                  CASE a.risk_level
                    WHEN 'severe_overdue' THEN 0
                    WHEN 'overdue' THEN 1
                    WHEN 'warning_soon' THEN 2
                    ELSE 3
                  END,
                  CASE a.status WHEN 'open' THEN 0 WHEN 'acknowledged' THEN 1 ELSE 2 END,
                  a.due_date ASC,
                  datetime(a.updated_time) DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        rules_by_channel = self._load_channel_rules_grouped()
        return {
            "items": [
                _alert_to_api(r, rules_by_channel=rules_by_channel) for r in rows
            ],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    def summary_counts(self) -> dict[str, int]:
        excl = sla_excluded_channels_params()
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT a.risk_level, a.status, COUNT(*) AS c
                FROM {TABLE_NAME} a
                INNER JOIN {SHIPMENTS_TABLE} s ON s.id = a.shipment_id
                WHERE {sla_excluded_channels_sql("s.channel_code")}
                GROUP BY a.risk_level, a.status
                """,
                excl,
            ).fetchall()
            exc_row = self._conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {SHIPMENTS_TABLE}
                WHERE exception_code IS NOT NULL AND TRIM(exception_code) != ''
                """
            ).fetchone()
        pending_open = 0
        severe = 0
        overdue = 0
        warning_soon = 0
        for row in rows:
            rl = row["risk_level"]
            st = row["status"]
            count = int(row["c"] or 0)
            if st in ACTIVE_STATUSES:
                pending_open += count
                if rl == RISK_SEVERE_OVERDUE:
                    severe += count
                elif rl == RISK_OVERDUE:
                    overdue += count
                elif rl == "warning_soon":
                    warning_soon += count
        return {
            "pendingOpen": pending_open,
            "severeOverdue": severe,
            "overdue": overdue,
            "warningSoon": warning_soon,
            "currentExceptions": int(exc_row["c"] or 0),
        }

    def list_todo_notifications(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """顶栏待办：已超时/严重超时且待处理。"""
        lim = max(1, min(limit, 50))
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT a.*, s.customer, s.carrier_code AS ship_carrier_code,
                       COALESCE(ec.name_zh, s.exception_code) AS exception_name_zh,
                       csr.estimated_days AS rule_estimated_days,
                       {_FOLLOW_UP_STATS_SQL}
                FROM {TABLE_NAME} a
                INNER JOIN {SHIPMENTS_TABLE} s ON s.id = a.shipment_id
                LEFT JOIN {EXCEPTION_CODES_TABLE} ec ON ec.code = s.exception_code
                LEFT JOIN {RULES_TABLE} csr ON csr.id = a.rule_id
                WHERE a.status = ?
                  AND a.risk_level IN (?, ?)
                  AND {sla_excluded_channels_sql("s.channel_code")}
                ORDER BY
                  CASE a.risk_level WHEN ? THEN 0 ELSE 1 END,
                  a.due_date ASC,
                  datetime(a.updated_time) DESC
                LIMIT ?
                """,
                (
                    STATUS_OPEN,
                    RISK_OVERDUE,
                    RISK_SEVERE_OVERDUE,
                    RISK_SEVERE_OVERDUE,
                    *sla_excluded_channels_params(),
                    lim,
                ),
            ).fetchall()
        rules_by_channel = self._load_channel_rules_grouped()
        return [_alert_to_api(r, rules_by_channel=rules_by_channel) for r in rows]

    def count_todo(self) -> int:
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT COUNT(*) AS c
                FROM {TABLE_NAME} a
                INNER JOIN {SHIPMENTS_TABLE} s ON s.id = a.shipment_id
                WHERE a.status = ? AND a.risk_level IN (?, ?)
                  AND {sla_excluded_channels_sql("s.channel_code")}
                """,
                (STATUS_OPEN, RISK_OVERDUE, RISK_SEVERE_OVERDUE, *sla_excluded_channels_params()),
            ).fetchone()
        return int(row["c"] or 0)

    def follow_up(self, alert_id: str) -> bool:
        """记录一次跟进，并将预警置为已跟进（可重复）。"""
        aid = alert_id.strip()
        now = now_str()
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT status FROM {TABLE_NAME} WHERE id = ?",
                (aid,),
            ).fetchone()
            if not row:
                return False
            status = (row["status"] or "").strip()
            if status not in (STATUS_OPEN, STATUS_ACKNOWLEDGED):
                return False
            self._conn.execute(
                f"""
                INSERT INTO {FOLLOWUPS_TABLE} (id, alert_id, followed_time, created_time)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), aid, now, now),
            )
            self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET status = ?, acknowledged_time = ?, updated_time = ?
                WHERE id = ?
                """,
                (STATUS_ACKNOWLEDGED, now, now, aid),
            )
            self._conn.commit()
        return True

    def acknowledge(self, alert_id: str) -> bool:
        """兼容旧接口：等同 follow_up。"""
        return self.follow_up(alert_id)

    def resolve_alert(self, alert_id: str) -> bool:
        """人工标记已解决。"""
        aid = alert_id.strip()
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET status = ?, resolved_time = ?, updated_time = ?
                WHERE id = ? AND status IN (?, ?)
                """,
                (STATUS_RESOLVED, now, now, aid, STATUS_OPEN, STATUS_ACKNOWLEDGED),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def ignore(self, alert_id: str) -> bool:
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET status = ?, ignored_time = ?, updated_time = ?
                WHERE id = ? AND status IN ('open', 'acknowledged')
                """,
                (STATUS_IGNORED, now, now, alert_id.strip()),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def mark_converted(
        self,
        alert_id: str,
        *,
        exception_code: str,
        event_id: str,
    ) -> bool:
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET status = ?, converted_exception_code = ?, converted_event_id = ?,
                    updated_time = ?
                WHERE id = ? AND status IN ('open', 'acknowledged')
                """,
                (
                    STATUS_CONVERTED,
                    exception_code.strip(),
                    event_id.strip(),
                    now,
                    alert_id.strip(),
                ),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def update_note(self, alert_id: str, note: str) -> bool:
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET note = ?, updated_time = ?
                WHERE id = ?
                """,
                ((note or "").strip(), now, alert_id.strip()),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        aid = alert_id.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT a.*, s.customer, s.destination_port_code, s.atd, s.ata, s.warehouse_entry_time,
                       s.expected_delivery_time,
                       s.delivered_time, s.status_code, s.exception_code, s.exception_opened_time,
                       s.latest_tracking_desc,
                       s.latest_tracking_time, s.carrier_code AS ship_carrier_code,
                       cc.name_zh AS channel_name_zh,
                       COALESCE(ec.name_zh, s.exception_code) AS exception_name_zh,
                       last_closed_exc.opened_time AS last_exc_opened_time,
                       last_closed_exc.closed_time AS last_exc_closed_time,
                       csr.estimated_days AS rule_estimated_days,
                       {_FOLLOW_UP_STATS_SQL}
                FROM {TABLE_NAME} a
                INNER JOIN {SHIPMENTS_TABLE} s ON s.id = a.shipment_id
                LEFT JOIN channel_codes cc ON cc.code = a.channel_code
                LEFT JOIN {EXCEPTION_CODES_TABLE} ec ON ec.code = s.exception_code
                {_LAST_CLOSED_EXCEPTION_JOIN}
                LEFT JOIN {RULES_TABLE} csr ON csr.id = a.rule_id
                WHERE a.id = ?
                """,
                (aid,),
            ).fetchone()
        rules_by_channel = self._load_channel_rules_grouped()
        return _alert_to_api(row, rules_by_channel=rules_by_channel) if row else None
