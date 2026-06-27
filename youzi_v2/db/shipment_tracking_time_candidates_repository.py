"""运单轨迹时间候选 CRUD。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .shipment_tracking_time_candidates_table import TABLE_NAME


def _optional(row: sqlite3.Row, key: str, default: Any = "") -> Any:
    return row[key] if key in row.keys() else default


def _row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "shipmentId": row["shipment_id"],
        "fieldName": row["field_name"],
        "candidateValue": row["candidate_value"],
        "compareValue": _optional(row, "compare_value"),
        "recommendedSource": _optional(row, "recommended_source"),
        "compareSource": _optional(row, "compare_source"),
        "sourceTrackId": row["source_track_id"],
        "sourceTrackTime": row["source_track_time"],
        "sourceTrackDesc": row["source_track_desc"],
        "compareSourceTrackId": _optional(row, "compare_source_track_id"),
        "compareSourceTrackTime": _optional(row, "compare_source_track_time"),
        "compareSourceTrackDesc": _optional(row, "compare_source_track_desc"),
        "confidence": row["confidence"],
        "reviewStatus": row["review_status"],
        "reviewReason": row["review_reason"],
        "applied": bool(row["applied"]),
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


class ShipmentTrackingTimeCandidatesRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_for_shipment(self, shipment_id: str) -> list[dict[str, Any]]:
        sid = shipment_id.strip()
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE shipment_id = ?
                ORDER BY field_name
                """,
                (sid,),
            ).fetchall()
        return [_row_to_api(r) for r in rows]

    def list_pending_reviews(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        with self._database.lock:
            total = self._conn.execute(
                f"""
                SELECT COUNT(*) FROM {TABLE_NAME}
                WHERE review_status = 'pending_review'
                """
            ).fetchone()[0]
            rows = self._conn.execute(
                f"""
                SELECT c.*, s.shipment_no, s.expected_delivery_time, s.delivered_time
                FROM {TABLE_NAME} c
                INNER JOIN shipments s ON s.id = c.shipment_id
                WHERE c.review_status = 'pending_review'
                ORDER BY c.updated_time DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        items = []
        for row in rows:
            item = _row_to_api(row)
            item["shipmentNo"] = row["shipment_no"]
            if "expected_delivery_time" in row.keys():
                item["expectedDeliveryTime"] = row["expected_delivery_time"]
            if "delivered_time" in row.keys():
                item["deliveredTime"] = row["delivered_time"]
            items.append(item)
        return {
            "items": items,
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
        }

    def upsert_candidate(
        self,
        shipment_id: str,
        *,
        field_name: str,
        candidate_value: str,
        source_track_id: str,
        source_track_time: str,
        source_track_desc: str,
        compare_value: str = "",
        recommended_source: str = "",
        compare_source: str = "",
        compare_source_track_id: str = "",
        compare_source_track_time: str = "",
        compare_source_track_desc: str = "",
        confidence: str = "high",
        review_status: str = "auto_confirmed",
        review_reason: str = "",
        applied: bool = False,
    ) -> dict[str, Any]:
        sid = shipment_id.strip()
        fname = field_name.strip().lower()
        now = now_str()
        with self._database.lock:
            existing = self._conn.execute(
                f"""
                SELECT id FROM {TABLE_NAME}
                WHERE shipment_id = ? AND field_name = ?
                """,
                (sid, fname),
            ).fetchone()
            if existing:
                rid = str(existing["id"])
                self._conn.execute(
                    f"""
                    UPDATE {TABLE_NAME}
                    SET candidate_value = ?,
                        compare_value = ?,
                        recommended_source = ?,
                        compare_source = ?,
                        source_track_id = ?,
                        source_track_time = ?,
                        source_track_desc = ?,
                        compare_source_track_id = ?,
                        compare_source_track_time = ?,
                        compare_source_track_desc = ?,
                        confidence = ?,
                        review_status = ?,
                        review_reason = ?,
                        applied = ?,
                        updated_time = ?
                    WHERE id = ?
                    """,
                    (
                        candidate_value,
                        compare_value,
                        recommended_source,
                        compare_source,
                        source_track_id,
                        source_track_time,
                        source_track_desc,
                        compare_source_track_id,
                        compare_source_track_time,
                        compare_source_track_desc,
                        confidence,
                        review_status,
                        review_reason,
                        1 if applied else 0,
                        now,
                        rid,
                    ),
                )
            else:
                rid = str(uuid.uuid4())
                self._conn.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (
                        id, shipment_id, field_name, candidate_value,
                        compare_value, recommended_source, compare_source,
                        source_track_id, source_track_time, source_track_desc,
                        compare_source_track_id, compare_source_track_time,
                        compare_source_track_desc,
                        confidence, review_status, review_reason, applied,
                        created_time, updated_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rid,
                        sid,
                        fname,
                        candidate_value,
                        compare_value,
                        recommended_source,
                        compare_source,
                        source_track_id,
                        source_track_time,
                        source_track_desc,
                        compare_source_track_id,
                        compare_source_track_time,
                        compare_source_track_desc,
                        confidence,
                        review_status,
                        review_reason,
                        1 if applied else 0,
                        now,
                        now,
                    ),
                )
            self._conn.commit()
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (rid,)
            ).fetchone()
        return _row_to_api(row)

    def delete_field(self, shipment_id: str, field_name: str) -> None:
        with self._database.lock:
            self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE shipment_id = ? AND field_name = ?",
                (shipment_id.strip(), field_name.strip().lower()),
            )
            self._conn.commit()

    def mark_review(
        self,
        candidate_id: str,
        *,
        review_status: str,
        review_reason: str = "",
        applied: bool | None = None,
        candidate_value: str | None = None,
    ) -> dict[str, Any] | None:
        cid = candidate_id.strip()
        now = now_str()
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (cid,)
            ).fetchone()
            if not row:
                return None
            sets = ["review_status = ?", "review_reason = ?", "updated_time = ?"]
            params: list[Any] = [review_status, review_reason, now]
            if applied is not None:
                sets.append("applied = ?")
                params.append(1 if applied else 0)
            if candidate_value is not None:
                sets.append("candidate_value = ?")
                params.append(candidate_value)
            params.append(cid)
            self._conn.execute(
                f"UPDATE {TABLE_NAME} SET {', '.join(sets)} WHERE id = ?",
                params,
            )
            self._conn.commit()
            updated = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (cid,)
            ).fetchone()
        return _row_to_api(updated)
