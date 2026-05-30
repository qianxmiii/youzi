"""运单异常事件：标记、解除、历史查询。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from .datetime_util import now_str, normalize_tracking_time
from .shipment_exception_events_table import TABLE_NAME as EVENTS_TABLE
from .shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from .exception_duration import duration_seconds, format_duration


def _event_to_api(row: sqlite3.Row) -> dict[str, Any]:
    opened = row["opened_time"] or ""
    closed = row["closed_time"]
    secs = duration_seconds(opened, closed)
    return {
        "id": row["id"],
        "shipmentNo": row["shipment_no"],
        "exceptionCode": row["exception_code"],
        "openedTime": opened,
        "closedTime": closed,
        "note": row["note"],
        "durationSeconds": secs,
        "durationLabel": format_duration(secs, opened_time=opened, closed_time=closed),
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


def _normalize_event_time(raw: str | None, *, field_label: str) -> str:
    if raw is None or not str(raw).strip():
        return now_str()
    text = normalize_tracking_time(str(raw).strip())
    if not text:
        raise ValueError(f"{field_label}格式无效，请使用 YYYY-MM-DD HH:mm:ss")
    return text


class ShipmentExceptionEventsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _validate_exception_code(self, code: str) -> str:
        c = code.strip().upper()
        if not c:
            raise ValueError("异常类型不能为空")
        with self._database.lock:
            row = self._conn.execute(
                """
                SELECT code FROM shipment_exception_codes
                WHERE code = ? AND is_active = 1
                """,
                (c,),
            ).fetchone()
        if row is None:
            raise ValueError(f"未知异常类型: {code}")
        return str(row["code"])

    def list_by_shipment_no(
        self,
        shipment_no: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        sn = shipment_no.strip()
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {EVENTS_TABLE} WHERE shipment_no = ?",
                (sn,),
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT * FROM {EVENTS_TABLE}
                WHERE shipment_no = ?
                ORDER BY datetime(opened_time) DESC, datetime(created_time) DESC
                LIMIT ? OFFSET ?
                """,
                (sn, limit, offset),
            ).fetchall()
        return {
            "items": [_event_to_api(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def open_for_shipment_nos(
        self,
        shipment_nos: list[str],
        exception_code: str,
        *,
        note: str | None = None,
        opened_time: str | None = None,
    ) -> dict[str, Any]:
        code = self._validate_exception_code(exception_code)
        note_text = (note or "").strip() or None
        opened_at = _normalize_event_time(opened_time, field_label="异常开始时间")
        now = now_str()
        close_prev_at = opened_at if opened_at <= now else now
        opened = 0
        skipped: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []

        unique = list(dict.fromkeys(n.strip() for n in shipment_nos if n and n.strip()))
        with self._database.lock:
            for sn in unique:
                try:
                    ship = self._conn.execute(
                        f"SELECT id, exception_code FROM {SHIPMENTS_TABLE} WHERE shipment_no = ?",
                        (sn,),
                    ).fetchone()
                    if ship is None:
                        errors.append({"shipmentNo": sn, "message": "运单不存在"})
                        continue
                    if (ship["exception_code"] or "").strip() == code:
                        skipped.append({"shipmentNo": sn, "message": "已是该异常状态"})
                        continue

                    self._conn.execute(
                        f"""
                        UPDATE {EVENTS_TABLE}
                        SET closed_time = ?, updated_time = ?
                        WHERE shipment_no = ? AND (closed_time IS NULL OR TRIM(closed_time) = '')
                        """,
                        (close_prev_at, now, sn),
                    )
                    event_id = str(uuid.uuid4())
                    self._conn.execute(
                        f"""
                        INSERT INTO {EVENTS_TABLE} (
                            id, shipment_no, exception_code, opened_time, closed_time,
                            note, created_time, updated_time
                        ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?)
                        """,
                        (event_id, sn, code, opened_at, note_text, now, now),
                    )
                    self._conn.execute(
                        f"""
                        UPDATE {SHIPMENTS_TABLE}
                        SET exception_code = ?, exception_opened_time = ?, updated_time = ?
                        WHERE shipment_no = ?
                        """,
                        (code, opened_at, now, sn),
                    )
                    opened += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append({"shipmentNo": sn, "message": str(exc)})
            self._conn.commit()

        return {"ok": True, "opened": opened, "skipped": skipped, "errors": errors}

    def close_for_shipment_nos(
        self,
        shipment_nos: list[str],
        *,
        note: str | None = None,
        closed_time: str | None = None,
    ) -> dict[str, Any]:
        note_text = (note or "").strip() or None
        closed_at = _normalize_event_time(closed_time, field_label="异常结束时间")
        now = now_str()
        closed = 0
        skipped: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []

        unique = list(dict.fromkeys(n.strip() for n in shipment_nos if n and n.strip()))
        with self._database.lock:
            for sn in unique:
                try:
                    ship = self._conn.execute(
                        f"""
                        SELECT exception_code, exception_opened_time
                        FROM {SHIPMENTS_TABLE} WHERE shipment_no = ?
                        """,
                        (sn,),
                    ).fetchone()
                    if ship is None:
                        errors.append({"shipmentNo": sn, "message": "运单不存在"})
                        continue
                    if not (ship["exception_code"] or "").strip():
                        skipped.append({"shipmentNo": sn, "message": "当前无异常"})
                        continue

                    opened_raw = (ship["exception_opened_time"] or "").strip()
                    if opened_raw:
                        opened_norm = normalize_tracking_time(opened_raw) or opened_raw
                        if closed_at < opened_norm:
                            errors.append(
                                {
                                    "shipmentNo": sn,
                                    "message": "结束时间不能早于开始时间",
                                }
                            )
                            continue

                    if note_text:
                        self._conn.execute(
                            f"""
                            UPDATE {EVENTS_TABLE}
                            SET closed_time = ?, updated_time = ?, note = ?
                            WHERE shipment_no = ?
                              AND (closed_time IS NULL OR TRIM(closed_time) = '')
                            """,
                            (closed_at, now, note_text, sn),
                        )
                    else:
                        self._conn.execute(
                            f"""
                            UPDATE {EVENTS_TABLE}
                            SET closed_time = ?, updated_time = ?
                            WHERE shipment_no = ?
                              AND (closed_time IS NULL OR TRIM(closed_time) = '')
                            """,
                            (closed_at, now, sn),
                        )
                    self._conn.execute(
                        f"""
                        UPDATE {SHIPMENTS_TABLE}
                        SET exception_code = NULL, exception_opened_time = NULL, updated_time = ?
                        WHERE shipment_no = ?
                        """,
                        (now, sn),
                    )
                    closed += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append({"shipmentNo": sn, "message": str(exc)})
            self._conn.commit()

        return {"ok": True, "closed": closed, "skipped": skipped, "errors": errors}

    def list_active_exception_codes(self) -> list[str]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT DISTINCT exception_code AS v FROM {SHIPMENTS_TABLE}
                WHERE exception_code IS NOT NULL AND TRIM(exception_code) != ''
                ORDER BY exception_code
                """
            ).fetchall()
        return [str(r["v"]) for r in rows]
