"""异常跟进提醒：待办通知 CRUD 与扫描辅助。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .internal_tracking_logs_table import LATEST_INTERNAL_LOG_JOIN, LATEST_INTERNAL_LOG_TIME
from .shipment_order_status import WORKSPACE_TRANSIT, workspace_status_filter_sql
from .shipment_sla import sql_sla_delivered, sql_sla_not_delivered
from .shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from .shipment_exception_followup_table import TABLE_NAME

EXCEPTION_CODES_TABLE = "shipment_exception_codes"
_TRANSIT_SQL, _TRANSIT_PARAMS = workspace_status_filter_sql(WORKSPACE_TRANSIT)
_ACTIVE_TRANSIT_SQL = f"{_TRANSIT_SQL} AND {sql_sla_not_delivered('s.route_status')}"


def _format_followup_display_message(row: sqlite3.Row) -> str:
    """统一展示文案，不暴露分档间隔；兼容库内旧 message。"""
    sn = (row["shipment_no"] or "").strip()
    days_open = int(row["days_open"] or 0)
    exc_label = "异常"
    if "exception_name_zh" in row.keys():
        exc_label = (row["exception_name_zh"] or "").strip()
    if not exc_label:
        exc_label = (row["exception_code"] or "").strip() or "异常"
    return f"运单 {sn} · {exc_label}。异常已持续 {days_open} 天，请跟进。"


def _notification_to_api(row: sqlite3.Row) -> dict[str, Any]:
    read_at = (row["read_at"] or "").strip()
    resolved_at = (row["resolved_at"] or "").strip()
    out: dict[str, Any] = {
        "id": row["id"],
        "shipmentId": row["shipment_id"],
        "shipmentNo": row["shipment_no"],
        "exceptionCode": row["exception_code"],
        "severity": row["severity"],
        "title": row["title"],
        "message": _format_followup_display_message(row),
        "daysOpen": int(row["days_open"] or 0),
        "followupIntervalDays": int(row["followup_interval_days"] or 3),
        "eventKey": row["event_key"],
        "triggeredAt": row["triggered_at"],
        "readAt": read_at or None,
        "resolvedAt": resolved_at or None,
    }
    if "customer" in row.keys():
        out["customer"] = (row["customer"] or "").strip() or None
    if "exception_name_zh" in row.keys():
        out["exceptionNameZh"] = (row["exception_name_zh"] or "").strip() or None
    return out


class ShipmentExceptionFollowupRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_active_exception_shipments(self) -> list[dict[str, Any]]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT s.id, s.shipment_no, s.exception_code, s.exception_opened_time,
                       s.customer, s.atd, {LATEST_INTERNAL_LOG_TIME} AS latest_tracking_time,
                       COALESCE(ec.name_zh, s.exception_code) AS exception_name_zh
                FROM {SHIPMENTS_TABLE} s
                {LATEST_INTERNAL_LOG_JOIN}
                LEFT JOIN {EXCEPTION_CODES_TABLE} ec ON ec.code = s.exception_code
                WHERE s.exception_code IS NOT NULL AND TRIM(s.exception_code) != ''
                  AND {_ACTIVE_TRANSIT_SQL}
                ORDER BY s.shipment_no
                """,
                _TRANSIT_PARAMS,
            ).fetchall()
        return [dict(r) for r in rows]

    def last_followup_anchor(self, shipment_no: str) -> str | None:
        sn = shipment_no.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT triggered_at, resolved_at FROM {TABLE_NAME}
                WHERE shipment_no = ?
                ORDER BY datetime(
                  COALESCE(NULLIF(TRIM(resolved_at), ''), triggered_at)
                ) DESC
                LIMIT 1
                """,
                (sn,),
            ).fetchone()
        if not row:
            return None
        resolved = (row["resolved_at"] or "").strip()
        if resolved:
            return resolved
        return (row["triggered_at"] or "").strip() or None

    def record_manual_followup(self, shipment_id: str) -> bool:
        """原子记录跟进并处理已有待办；不关闭运单异常。"""
        now = now_str()
        with self._database.lock:
            row = self._conn.execute(
                f"""SELECT s.shipment_no, s.exception_code FROM {SHIPMENTS_TABLE} s
                    WHERE s.id = ? AND {_ACTIVE_TRANSIT_SQL}""",
                (shipment_id, *_TRANSIT_PARAMS),
            ).fetchone()
            if not row or not (row["exception_code"] or "").strip():
                return False
            try:
                self._conn.execute(
                    f"UPDATE {TABLE_NAME} SET resolved_at = ?, read_at = ?, updated_time = ? "
                    "WHERE shipment_no = ? AND TRIM(COALESCE(resolved_at, '')) = ''",
                    (now, now, now, row["shipment_no"]),
                )
                self._conn.execute(
                    f"""INSERT INTO {TABLE_NAME} (
                        id, shipment_id, shipment_no, exception_code, severity, title, message,
                        days_open, followup_interval_days, event_key, triggered_at, read_at,
                        resolved_at, created_time, updated_time
                    ) VALUES (?, ?, ?, ?, 'info', '人工异常已跟进', '', 0, 7, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), shipment_id, row["shipment_no"], row["exception_code"],
                     f"manual-followup:{uuid.uuid4()}", now, now, now, now, now),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        return True

    def has_pending_followup(self, shipment_no: str) -> bool:
        sn = shipment_no.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT 1 FROM {TABLE_NAME}
                WHERE shipment_no = ?
                  AND (resolved_at IS NULL OR TRIM(resolved_at) = '')
                LIMIT 1
                """,
                (sn,),
            ).fetchone()
        return row is not None

    def create_followup_notification(
        self,
        *,
        shipment_id: str,
        shipment_no: str,
        exception_code: str,
        title: str,
        message: str,
        severity: str,
        days_open: int,
        followup_interval_days: int,
        event_key: str,
    ) -> bool:
        key = event_key.strip()
        now = now_str()
        with self._database.lock:
            existing = self._conn.execute(
                f"SELECT id FROM {TABLE_NAME} WHERE event_key = ?",
                (key,),
            ).fetchone()
            if existing:
                return False
            self._conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, shipment_id, shipment_no, exception_code, severity,
                    title, message, days_open, followup_interval_days,
                    event_key, triggered_at, read_at, resolved_at,
                    created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    shipment_id.strip(),
                    shipment_no.strip(),
                    exception_code.strip(),
                    severity,
                    title,
                    message,
                    int(days_open),
                    int(followup_interval_days),
                    key,
                    now,
                    now,
                    now,
                ),
            )
            self._conn.commit()
        return True

    def resolve_all_pending_for_shipment(self, shipment_no: str) -> int:
        sn = shipment_no.strip()
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET resolved_at = ?, read_at = CASE
                      WHEN read_at IS NULL OR TRIM(read_at) = '' THEN ?
                      ELSE read_at END,
                    updated_time = ?
                WHERE shipment_no = ?
                  AND (resolved_at IS NULL OR TRIM(resolved_at) = '')
                """,
                (now, now, now, sn),
            )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def resolve_pending_for_delivered_shipments(self) -> int:
        """扫描兜底：已签收运单上未完成的跟进待办批量关闭。"""
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET resolved_at = ?, read_at = CASE
                      WHEN read_at IS NULL OR TRIM(read_at) = '' THEN ?
                      ELSE read_at END,
                    updated_time = ?
                WHERE (resolved_at IS NULL OR TRIM(resolved_at) = '')
                  AND shipment_id IN (
                    SELECT id FROM {SHIPMENTS_TABLE}
                    WHERE {sql_sla_delivered("route_status")}
                  )
                """,
                (now, now, now),
            )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def list_pending_notifications(self, *, limit: int = 20) -> list[dict[str, Any]]:
        lim = max(1, min(limit, 50))
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT n.*, s.customer,
                       COALESCE(ec.name_zh, n.exception_code) AS exception_name_zh
                FROM {TABLE_NAME} n
                JOIN {SHIPMENTS_TABLE} s ON s.id = n.shipment_id
                LEFT JOIN {EXCEPTION_CODES_TABLE} ec ON ec.code = n.exception_code
                WHERE (n.resolved_at IS NULL OR TRIM(n.resolved_at) = '')
                  AND {_ACTIVE_TRANSIT_SQL}
                ORDER BY datetime(n.triggered_at) DESC
                LIMIT ?
                """,
                (*_TRANSIT_PARAMS, lim),
            ).fetchall()
        return [_notification_to_api(r) for r in rows]

    def count_pending(self) -> int:
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {TABLE_NAME} n
                JOIN {SHIPMENTS_TABLE} s ON s.id = n.shipment_id
                WHERE (n.resolved_at IS NULL OR TRIM(n.resolved_at) = '')
                  AND {_ACTIVE_TRANSIT_SQL}
                """,
                _TRANSIT_PARAMS,
            ).fetchone()
        return int(row["c"] or 0)

    def mark_read(self, notification_id: str) -> bool:
        nid = notification_id.strip()
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET read_at = ?, updated_time = ?
                WHERE id = ? AND (read_at IS NULL OR TRIM(read_at) = '')
                """,
                (now, now, nid),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def mark_resolved(self, notification_id: str) -> bool:
        nid = notification_id.strip()
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET resolved_at = ?, read_at = CASE
                      WHEN read_at IS NULL OR TRIM(read_at) = '' THEN ?
                      ELSE read_at END,
                    updated_time = ?
                WHERE id = ? AND (resolved_at IS NULL OR TRIM(resolved_at) = '')
                """,
                (now, now, now, nid),
            )
            self._conn.commit()
            return cur.rowcount > 0
