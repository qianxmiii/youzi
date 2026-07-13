"""运单催款跟进与催款列表查询。"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date
from typing import Any

from .connection import Database
from .customers_table import TABLE_NAME as CUSTOMERS_TABLE
from .datetime_util import now_str
from .shipment_payment_followups_table import TABLE_NAME as FOLLOWUPS_TABLE
from .shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from .tracking_freshness import FCL_CARRIER_NAME_ZH, FCL_CHANNEL_CODE
from ..services.payment_reminder_rules import (
    SETTLEMENT_METHODS,
    compute_payment_reminder,
    is_unpaid_payment_status,
    matches_scope,
    reminder_sort_key,
)


def _followup_row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "shipmentId": row["shipment_id"],
        "shipmentNo": row["shipment_no"],
        "customer": row["customer"] or "",
        "settlementMethod": row["settlement_method"] or "",
        "reminderType": row["reminder_type"] or "",
        "dueDate": row["due_date"] or "",
        "followupTime": row["followup_time"],
        "note": row["note"] or "",
        "createdBy": row["created_by"] or "",
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


class ShipmentPaymentFollowupsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _shipment_row_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {k: row[k] for k in row.keys()}

    def _is_fcl_shipment(self, row: sqlite3.Row) -> bool:
        channel = (row["channel_code"] or "").strip() if "channel_code" in row.keys() else ""
        if channel.casefold() == FCL_CHANNEL_CODE.casefold():
            return True
        carrier = (row["carrier_code"] or "").strip() if "carrier_code" in row.keys() else ""
        if carrier.casefold() == FCL_CARRIER_NAME_ZH.casefold():
            return True
        channel_name = (
            (row["_channel_name_zh"] or "").strip()
            if "_channel_name_zh" in row.keys()
            else ""
        )
        if channel_name.casefold() == FCL_CARRIER_NAME_ZH.casefold():
            return True
        return False

    def _build_reminder_item(
        self,
        row: sqlite3.Row,
        *,
        today: date | None = None,
    ) -> dict[str, Any]:
        data = self._shipment_row_dict(row)
        settlement_method = None
        settlement_day = None
        if "settlement_method" in row.keys():
            raw_method = row["settlement_method"]
            settlement_method = (raw_method or "").strip() or None
        if "settlement_day" in row.keys() and row["settlement_day"] is not None:
            try:
                settlement_day = int(row["settlement_day"])
            except (TypeError, ValueError):
                settlement_day = None

        calc = compute_payment_reminder(
            data,
            settlement_method=settlement_method,
            settlement_day=settlement_day,
            today=today,
        )
        payment_status = (row["payment_status"] or "").strip().upper() or None
        if payment_status not in ("PAID", "UNPAID"):
            payment_status = "UNPAID" if is_unpaid_payment_status(payment_status) else None

        bill_of_lading_no = (
            (row["bill_of_lading_no"] or "").strip()
            if "bill_of_lading_no" in row.keys()
            else ""
        )
        container_no = (
            (row["container_no"] or "").strip() if "container_no" in row.keys() else ""
        )

        return {
            "shipmentId": row["id"],
            "shipmentNo": row["shipment_no"],
            "customer": row["customer"] or "",
            "customerNo": (row["customer_no"] or "") if "customer_no" in row.keys() else "",
            "billOfLadingNo": bill_of_lading_no,
            "containerNo": container_no,
            "isFcl": self._is_fcl_shipment(row),
            "channelCode": row["channel_code"] or "",
            "channelNameZh": (
                row["_channel_name_zh"] if "_channel_name_zh" in row.keys() else ""
            )
            or "",
            "statusCode": (
                (row["status_code"] or "").strip()
                if "status_code" in row.keys()
                else ""
            )
            or "UNKNOWN",
            "latestTrackingTime": (
                row["latest_tracking_time"]
                if "latest_tracking_time" in row.keys()
                else None
            ),
            "latestTrackingDesc": (
                row["latest_tracking_desc"] if "latest_tracking_desc" in row.keys() else ""
            )
            or "",
            "paymentStatus": payment_status or "UNPAID",
            "followupCount": int(row["followup_count"] or 0)
            if "followup_count" in row.keys()
            else 0,
            "lastFollowupTime": (
                row["last_followup_time"] if "last_followup_time" in row.keys() else None
            ),
            "lastFollowupNote": (
                row["last_followup_note"] if "last_followup_note" in row.keys() else ""
            )
            or "",
            **calc,
        }

    def list_reminders(
        self,
        *,
        scope: str = "todo",
        customer: str | None = None,
        settlement_method: str | None = None,
        reminder_type: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        today = date.today()

        conditions = [
            "(s.payment_status IS NULL OR TRIM(s.payment_status) = '' OR UPPER(s.payment_status) != 'PAID')"
        ]
        params: list[Any] = []

        if customer and customer.strip():
            conditions.append("TRIM(s.customer) = ?")
            params.append(customer.strip())

        if settlement_method and settlement_method.strip():
            sm = settlement_method.strip().upper()
            if sm == "UNSET":
                conditions.append(
                    "(cu.settlement_method IS NULL OR TRIM(cu.settlement_method) = '')"
                )
            elif sm in SETTLEMENT_METHODS:
                conditions.append("UPPER(TRIM(cu.settlement_method)) = ?")
                params.append(sm)

        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append(
                "(s.shipment_no LIKE ? OR s.customer_no LIKE ? OR s.customer_shipment_id LIKE ?)"
            )
            params.extend([q, q, q])

        where = f"WHERE {' AND '.join(conditions)}"

        sql = f"""
            SELECT
                s.*,
                cc.name_zh AS _channel_name_zh,
                cu.settlement_method,
                cu.settlement_day,
                COALESCE(fu.followup_count, 0) AS followup_count,
                fu.last_followup_time,
                (
                    SELECT f2.note FROM {FOLLOWUPS_TABLE} f2
                    WHERE f2.shipment_id = s.id
                    ORDER BY datetime(f2.followup_time) DESC, f2.created_time DESC
                    LIMIT 1
                ) AS last_followup_note
            FROM {SHIPMENTS_TABLE} s
            LEFT JOIN channel_codes cc ON s.channel_code = cc.code
            LEFT JOIN {CUSTOMERS_TABLE} cu ON TRIM(s.customer) = cu.customer_name
            LEFT JOIN (
                SELECT shipment_id,
                       COUNT(*) AS followup_count,
                       MAX(followup_time) AS last_followup_time
                FROM {FOLLOWUPS_TABLE}
                GROUP BY shipment_id
            ) fu ON fu.shipment_id = s.id
            {where}
            ORDER BY s.updated_time DESC, s.shipment_no
        """

        with self._database.lock:
            rows = self._conn.execute(sql, params).fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            item = self._build_reminder_item(row, today=today)
            if not matches_scope(item.get("reminderType") or "", scope):
                continue
            if reminder_type and reminder_type.strip():
                if (item.get("reminderType") or "") != reminder_type.strip():
                    continue
            items.append(item)

        items.sort(key=reminder_sort_key)
        total = len(items)
        page = items[offset : offset + limit]
        return {
            "items": page,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def list_followups(self, shipment_id: str) -> list[dict[str, Any]]:
        sid = shipment_id.strip()
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {FOLLOWUPS_TABLE}
                WHERE shipment_id = ?
                ORDER BY datetime(followup_time) DESC, created_time DESC
                """,
                (sid,),
            ).fetchall()
        return [_followup_row_to_api(r) for r in rows]

    def create_followup(
        self,
        shipment_id: str,
        *,
        note: str = "",
        created_by: str = "",
    ) -> dict[str, Any]:
        sid = shipment_id.strip()
        with self._database.lock:
            ship = self._conn.execute(
                f"""
                SELECT s.*, cu.settlement_method, cu.settlement_day
                FROM {SHIPMENTS_TABLE} s
                LEFT JOIN {CUSTOMERS_TABLE} cu ON TRIM(s.customer) = cu.customer_name
                WHERE s.id = ?
                """,
                (sid,),
            ).fetchone()
            if ship is None:
                raise KeyError(sid)

            item = self._build_reminder_item(ship)
            now = now_str()
            fid = str(uuid.uuid4())
            self._conn.execute(
                f"""
                INSERT INTO {FOLLOWUPS_TABLE} (
                    id, shipment_id, shipment_no, customer, settlement_method,
                    reminder_type, due_date, followup_time, note, created_by,
                    created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fid,
                    sid,
                    ship["shipment_no"],
                    item.get("customer") or "",
                    item.get("settlementMethod") or "",
                    item.get("reminderType") or "",
                    item.get("dueDate") or "",
                    now,
                    (note or "").strip(),
                    (created_by or "").strip(),
                    now,
                    now,
                ),
            )
            self._conn.commit()
            row = self._conn.execute(
                f"SELECT * FROM {FOLLOWUPS_TABLE} WHERE id = ?",
                (fid,),
            ).fetchone()
        if row is None:
            raise RuntimeError("跟进记录写入失败")
        return _followup_row_to_api(row)

    def batch_create_followups(
        self,
        shipment_ids: list[str],
        *,
        note: str = "",
        created_by: str = "",
    ) -> dict[str, Any]:
        created = 0
        failed = 0
        errors: list[dict[str, str]] = []
        for sid in shipment_ids:
            clean = (sid or "").strip()
            if not clean:
                failed += 1
                continue
            try:
                self.create_followup(clean, note=note, created_by=created_by)
                created += 1
            except KeyError:
                failed += 1
                if len(errors) < 20:
                    errors.append({"id": clean, "message": "运单不存在"})
            except Exception as exc:
                failed += 1
                if len(errors) < 20:
                    errors.append({"id": clean, "message": str(exc)})
        return {
            "total": len(shipment_ids),
            "created": created,
            "failed": failed,
            "errors": errors,
        }
