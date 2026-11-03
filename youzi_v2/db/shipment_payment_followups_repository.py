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
from .shipment_order_status import PRE_PORT_STATUSES
from .shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from .tracking_freshness import (
    FCL_CARRIER_NAME_ZH,
    FCL_CHANNEL_CODE,
    fcl_only_filter_sql,
)
from ..services.payment_reminder_rules import (
    SETTLEMENT_METHODS,
    SETTLEMENT_MONTHLY,
    compute_payment_reminder,
    is_unpaid_payment_status,
    matches_scope,
    reminder_sort_key,
)


def _receivable_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    amount = item.get("receivableCny")
    if amount is None:
        return (1, 0.0, reminder_sort_key(item))
    return (0, -float(amount), reminder_sort_key(item))


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
            "refShipmentNo": (
                (row["ref_shipment_no"] or "").strip()
                if "ref_shipment_no" in row.keys()
                else ""
            ),
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
            "ata": (row["ata"] or "").strip() if "ata" in row.keys() else "",
            "deliveredTime": (
                (row["delivered_time"] or "").strip()
                if "delivered_time" in row.keys()
                else ""
            ),
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
            "receivableCny": (
                float(row["receivable_cny"])
                if "receivable_cny" in row.keys() and row["receivable_cny"] is not None
                else None
            ),
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

    def _collect_reminder_items(
        self,
        *,
        scope: str = "todo",
        customer: str | None = None,
        settlement_method: str | None = None,
        reminder_type: str | None = None,
        followup_status: str | None = None,
        search: str | None = None,
        fcl_only: bool | None = None,
        channel_category: str | None = None,
        today: date | None = None,
    ) -> list[dict[str, Any]]:
        today = today or date.today()

        preport = sorted(PRE_PORT_STATUSES)
        preport_placeholders = ", ".join("?" for _ in preport)
        conditions = [
            "(s.payment_status IS NULL OR TRIM(s.payment_status) = '' OR UPPER(s.payment_status) != 'PAID')",
            f"TRIM(COALESCE(s.status_code, '')) NOT IN ({preport_placeholders})",
        ]
        params: list[Any] = list(preport)

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
                "(s.shipment_no LIKE ? OR s.customer_no LIKE ? OR s.ref_shipment_no LIKE ? OR s.customer_shipment_id LIKE ?)"
            )
            params.extend([q, q, q, q])

        if channel_category and channel_category.strip():
            conditions.append("TRIM(cc.category) = ?")
            params.append(channel_category.strip())

        fu_status = (followup_status or "").strip().lower()
        if fu_status in ("unfollowed", "none", "pending"):
            conditions.append("COALESCE(fu.followup_count, 0) = 0")
        elif fu_status in ("followed", "done"):
            conditions.append("COALESCE(fu.followup_count, 0) > 0")

        if fcl_only is True:
            frag, frag_params = fcl_only_filter_sql(include_fcl=True)
            conditions.append(frag)
            params.extend(frag_params)
        elif fcl_only is False:
            frag, frag_params = fcl_only_filter_sql(include_fcl=False)
            conditions.append(frag)
            params.extend(frag_params)

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
            if not matches_scope(
                item.get("reminderType") or "",
                scope,
                item.get("settlementMethod"),
            ):
                continue
            if reminder_type and reminder_type.strip():
                if (item.get("reminderType") or "") != reminder_type.strip():
                    continue
            items.append(item)

        items.sort(key=reminder_sort_key)
        return items

    def list_reminders(
        self,
        *,
        scope: str = "todo",
        customer: str | None = None,
        settlement_method: str | None = None,
        reminder_type: str | None = None,
        followup_status: str | None = None,
        search: str | None = None,
        fcl_only: bool | None = None,
        min_receivable: float | None = None,
        receivable_pending: bool = False,
        sort_by: str | None = None,
        channel_category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 10_000))
        offset = max(0, offset)
        items = self._collect_reminder_items(
            scope=scope,
            customer=customer,
            settlement_method=settlement_method,
            reminder_type=reminder_type,
            followup_status=followup_status,
            search=search,
            fcl_only=fcl_only,
            channel_category=channel_category,
        )
        if min_receivable is not None:
            threshold = float(min_receivable)
            items = [
                item
                for item in items
                if item.get("receivableCny") is not None
                and float(item["receivableCny"]) >= threshold
            ]
        if receivable_pending:
            items = [
                item
                for item in items
                if item.get("receivableCny") is None or float(item["receivableCny"]) <= 0
            ]
        if (sort_by or "").strip() == "receivable":
            items.sort(key=_receivable_sort_key)
        total = len(items)
        page = items[offset : offset + limit]
        return {
            "items": page,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def customer_ranking(
        self,
        *,
        scope: str = "todo",
        settlement_method: str | None = None,
        reminder_type: str | None = None,
        followup_status: str | None = None,
        search: str | None = None,
        fcl_only: bool | None = None,
        min_receivable: float | None = None,
        receivable_pending: bool = False,
        channel_category: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """当前筛选下按客户汇总大于 0 的应收。不含客户筛选，方便点排名后列表收窄而图仍在。"""
        items = self._collect_reminder_items(
            scope=scope,
            settlement_method=settlement_method,
            reminder_type=reminder_type,
            followup_status=followup_status,
            search=search,
            fcl_only=fcl_only,
            channel_category=channel_category,
        )
        pending_count = sum(
            1
            for item in items
            if item.get("receivableCny") is None or float(item["receivableCny"]) <= 0
        )
        if min_receivable is not None:
            threshold = float(min_receivable)
            items = [
                item
                for item in items
                if item.get("receivableCny") is not None
                and float(item["receivableCny"]) >= threshold
            ]
        if receivable_pending:
            items = [
                item
                for item in items
                if item.get("receivableCny") is None or float(item["receivableCny"]) <= 0
            ]
        buckets: dict[str, dict[str, Any]] = {}
        for item in items:
            raw = item.get("receivableCny")
            if raw is None or float(raw) <= 0:
                continue
            amount = float(raw)
            name = (item.get("customer") or "").strip() or "未填客户"
            bucket = buckets.get(name)
            if bucket is None:
                bucket = {
                    "customer": name,
                    "total": 0.0,
                    "overdue": 0.0,
                    "open": 0.0,
                    "count": 0,
                }
                buckets[name] = bucket
            bucket["total"] += amount
            bucket["count"] += 1
            if (item.get("reminderType") or "") == "overdue":
                bucket["overdue"] += amount
            else:
                bucket["open"] += amount
        ranked = sorted(buckets.values(), key=lambda row: (-row["total"], row["customer"]))
        for row in ranked:
            row["total"] = round(row["total"], 2)
            row["overdue"] = round(row["overdue"], 2)
            row["open"] = round(row["open"], 2)
        top = ranked[: max(1, min(limit, 100))]
        total_receivable = round(sum(row["total"] for row in ranked), 2)
        return {
            "items": top,
            "pendingCount": pending_count,
            "totalReceivable": total_receivable,
        }

    def reminder_summary(self, *, fcl_only: bool | None = False) -> dict[str, Any]:
        """侧栏/标题用：待催与全部未付款数量。默认排除整柜（与列表默认一致）。
        待催 / 逾期统计均排除月结（日常按票催款不关注月结对账）。
        """
        unpaid = self._collect_reminder_items(scope="all_unpaid", fcl_only=fcl_only)
        todo_count = sum(
            1
            for item in unpaid
            if matches_scope(
                item.get("reminderType") or "",
                "todo",
                item.get("settlementMethod"),
            )
        )
        overdue_count = sum(
            1
            for item in unpaid
            if (item.get("reminderType") or "") == "overdue"
            and (item.get("settlementMethod") or "").strip().upper() != SETTLEMENT_MONTHLY
        )
        return {
            "todoCount": todo_count,
            "allUnpaidCount": len(unpaid),
            "overdueCount": overdue_count,
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

    def set_collection_terms(
        self,
        shipment_ids: list[str],
        *,
        start_date: str,
        term_days: int = 21,
        advance_days: int = 7,
    ) -> dict[str, Any]:
        from ..db.shipment_sla import parse_date

        day = (start_date or "").strip()[:10]
        if parse_date(day) is None:
            raise ValueError("收款起算日无效")
        try:
            days = int(term_days)
        except (TypeError, ValueError) as exc:
            raise ValueError("账期无效") from exc
        if days < 1 or days > 3650:
            raise ValueError("账期须在 1 到 3650 天")
        try:
            advance = int(advance_days)
        except (TypeError, ValueError) as exc:
            raise ValueError("提前提醒天数无效") from exc
        if advance < 0 or advance > 365:
            raise ValueError("提前提醒天数须在 0 到 365 天")
        now = now_str()
        updated = 0
        missing = 0
        with self._database.lock:
            for sid in shipment_ids:
                clean = (sid or "").strip()
                if not clean:
                    continue
                cur = self._conn.execute(
                    f"""
                    UPDATE {SHIPMENTS_TABLE}
                    SET collection_start_date = ?, payment_term_days = ?,
                        reminder_advance_days = ?, updated_time = ?
                    WHERE id = ?
                    """,
                    (day, days, advance, now, clean),
                )
                if cur.rowcount:
                    updated += 1
                else:
                    missing += 1
            self._conn.commit()
        return {"updated": updated, "missing": missing}

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
