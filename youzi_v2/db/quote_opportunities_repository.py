"""报价机会、版本与跟进仓储。"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .quote_followups_table import TABLE_NAME as FOLLOWUPS_TABLE
from .quote_opportunities_table import TABLE_NAME as OPPORTUNITIES_TABLE
from .quote_versions_table import TABLE_NAME as VERSIONS_TABLE
from .shipment_sla import parse_date
from ..services.quote_followup_rules import (
    ACTIVE_STATUSES,
    CHANGE_INITIAL,
    CHANGE_REASONS,
    EXPIRING_SOON_DAYS,
    SCOPE_TODO,
    STATUS_CANCELLED,
    STATUS_FOLLOWING,
    STATUS_LOST,
    STATUS_QUOTED,
    STATUS_WON,
    classify_urgency,
    compute_next_followup_date,
    display_status,
    matches_scope,
    quote_sort_key,
    status_label,
)


def _opt_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _opt_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_get(row: sqlite3.Row, key: str, default: Any = None) -> Any:
    if key not in row.keys():
        return default
    return row[key]


class QuoteOpportunitiesRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _generate_quote_no(self, today: date | None = None) -> str:
        day = today or date.today()
        prefix = f"QT{day.strftime('%Y%m%d')}"
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT quote_no FROM {OPPORTUNITIES_TABLE}
                WHERE quote_no LIKE ?
                ORDER BY quote_no DESC
                LIMIT 1
                """,
                (f"{prefix}%",),
            ).fetchone()
        seq = 1
        if row and row["quote_no"]:
            tail = str(row["quote_no"])[len(prefix) :]
            try:
                seq = int(tail) + 1
            except ValueError:
                seq = 1
        return f"{prefix}{seq:04d}"

    def _version_to_api(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "quoteId": row["quote_id"],
            "versionNo": int(row["version_no"]),
            "versionTime": row["version_time"],
            "changeReason": row["change_reason"] or "",
            "productName": row["product_name"] or "",
            "addressText": row["address_text"] or "",
            "ctns": row["ctns"],
            "weightKg": row["weight_kg"],
            "volumeCbm": row["volume_cbm"],
            "quotedAmount": row["quoted_amount"],
            "quotedCurrency": row["quoted_currency"] or "",
            "profitAmount": row["profit_amount"],
            "profitCurrency": row["profit_currency"] or "",
            "profitRate": row["profit_rate"],
            "note": row["note"] or "",
            "createdTime": row["created_time"],
            "updatedTime": row["updated_time"],
        }

    def _followup_to_api(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "quoteId": row["quote_id"],
            "quoteVersionId": row["quote_version_id"] or "",
            "followupTime": row["followup_time"],
            "followupType": row["followup_type"] or "",
            "note": row["note"] or "",
            "nextFollowupDate": row["next_followup_date"] or "",
            "createdBy": row["created_by"] or "",
            "createdTime": row["created_time"],
            "updatedTime": row["updated_time"],
        }

    def _opportunity_to_api(
        self,
        row: sqlite3.Row,
        *,
        today: date | None = None,
        followup_count: int = 0,
        last_followup_time: str | None = None,
        last_followup_note: str = "",
    ) -> dict[str, Any]:
        check_day = today or date.today()
        status = (row["status"] or STATUS_QUOTED).strip().upper()
        deadline = parse_date(row["deadline_date"])
        next_fu = parse_date(row["next_followup_date"])
        disp = display_status(status, deadline, check_day)
        urgency = classify_urgency(
            status=status,
            next_followup=next_fu,
            deadline=deadline,
            today=check_day,
        )
        return {
            "id": row["id"],
            "quoteNo": row["quote_no"],
            "customerId": row["customer_id"] or "",
            "customerName": row["customer_name"] or "",
            "isNewCustomer": bool(int(row["is_new_customer"] or 0)),
            "customerInquiryNo": row["customer_inquiry_no"] or "",
            "quoteDate": (row["quote_date"] or "")[:10],
            "deadlineDate": (row["deadline_date"] or "")[:10],
            "followupIntervalDays": int(row["followup_interval_days"] or 1),
            "nextFollowupDate": (row["next_followup_date"] or "")[:10],
            "status": status,
            "displayStatus": disp,
            "statusLabel": status_label(disp),
            "owner": row["owner"] or "",
            "productName": row["product_name"] or "",
            "addressText": row["address_text"] or "",
            "ctns": row["ctns"],
            "weightKg": row["weight_kg"],
            "volumeCbm": row["volume_cbm"],
            "currentQuoteVersionId": row["current_quote_version_id"] or "",
            "currentQuotedAmount": row["current_quoted_amount"],
            "currentQuotedCurrency": row["current_quoted_currency"] or "",
            "currentProfitAmount": row["current_profit_amount"],
            "currentProfitCurrency": row["current_profit_currency"] or "",
            "currentProfitRate": row["current_profit_rate"],
            "lostReason": row["lost_reason"] or "",
            "note": row["note"] or "",
            "convertedShipmentId": row["converted_shipment_id"] or "",
            "convertedShipmentNo": row["converted_shipment_no"] or "",
            "convertedTime": row["converted_time"] or "",
            "followupCount": followup_count,
            "lastFollowupTime": last_followup_time,
            "lastFollowupNote": last_followup_note or "",
            "createdTime": row["created_time"],
            "updatedTime": row["updated_time"],
            "_urgency": urgency,
        }

    def get_by_id(self, quote_id: str) -> dict[str, Any] | None:
        sid = quote_id.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {OPPORTUNITIES_TABLE} WHERE id = ?",
                (sid,),
            ).fetchone()
            if row is None:
                return None
            agg = self._conn.execute(
                f"""
                SELECT COUNT(*) AS cnt, MAX(followup_time) AS last_time
                FROM {FOLLOWUPS_TABLE} WHERE quote_id = ?
                """,
                (sid,),
            ).fetchone()
            last_note = ""
            if agg and agg["last_time"]:
                note_row = self._conn.execute(
                    f"""
                    SELECT note FROM {FOLLOWUPS_TABLE}
                    WHERE quote_id = ?
                    ORDER BY datetime(followup_time) DESC, created_time DESC
                    LIMIT 1
                    """,
                    (sid,),
                ).fetchone()
                last_note = (note_row["note"] if note_row else "") or ""
        return self._opportunity_to_api(
            row,
            followup_count=int(agg["cnt"] or 0) if agg else 0,
            last_followup_time=agg["last_time"] if agg else None,
            last_followup_note=last_note,
        )

    def list_rows(
        self,
        *,
        scope: str = SCOPE_TODO,
        status: str | None = None,
        customer: str | None = None,
        is_new_customer: bool | None = None,
        owner: str | None = None,
        quote_date_from: str | None = None,
        quote_date_to: str | None = None,
        deadline_from: str | None = None,
        deadline_to: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        today = date.today()
        conditions: list[str] = []
        params: list[Any] = []

        if status and status.strip():
            conditions.append("UPPER(TRIM(q.status)) = ?")
            params.append(status.strip().upper())
        if customer and customer.strip():
            conditions.append("TRIM(q.customer_name) = ?")
            params.append(customer.strip())
        if is_new_customer is True:
            conditions.append("q.is_new_customer = 1")
        elif is_new_customer is False:
            conditions.append("COALESCE(q.is_new_customer, 0) = 0")
        if owner and owner.strip():
            conditions.append("TRIM(q.owner) = ?")
            params.append(owner.strip())
        if quote_date_from and quote_date_from.strip():
            conditions.append("substr(q.quote_date, 1, 10) >= ?")
            params.append(quote_date_from.strip()[:10])
        if quote_date_to and quote_date_to.strip():
            conditions.append("substr(q.quote_date, 1, 10) <= ?")
            params.append(quote_date_to.strip()[:10])
        if deadline_from and deadline_from.strip():
            conditions.append("substr(q.deadline_date, 1, 10) >= ?")
            params.append(deadline_from.strip()[:10])
        if deadline_to and deadline_to.strip():
            conditions.append("substr(q.deadline_date, 1, 10) <= ?")
            params.append(deadline_to.strip()[:10])
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append(
                "("
                "q.quote_no LIKE ? OR q.customer_inquiry_no LIKE ? "
                "OR q.customer_name LIKE ? OR q.product_name LIKE ? "
                "OR q.address_text LIKE ?"
                ")"
            )
            params.extend([q, q, q, q, q])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT
                q.*,
                COALESCE(fu.followup_count, 0) AS followup_count,
                fu.last_followup_time,
                (
                    SELECT f2.note FROM {FOLLOWUPS_TABLE} f2
                    WHERE f2.quote_id = q.id
                    ORDER BY datetime(f2.followup_time) DESC, f2.created_time DESC
                    LIMIT 1
                ) AS last_followup_note
            FROM {OPPORTUNITIES_TABLE} q
            LEFT JOIN (
                SELECT quote_id,
                       COUNT(*) AS followup_count,
                       MAX(followup_time) AS last_followup_time
                FROM {FOLLOWUPS_TABLE}
                GROUP BY quote_id
            ) fu ON fu.quote_id = q.id
            {where}
            ORDER BY q.updated_time DESC
        """
        with self._database.lock:
            rows = self._conn.execute(sql, params).fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            item = self._opportunity_to_api(
                row,
                today=today,
                followup_count=int(_row_get(row, "followup_count") or 0),
                last_followup_time=_row_get(row, "last_followup_time"),
                last_followup_note=_row_get(row, "last_followup_note") or "",
            )
            next_fu = parse_date(item.get("nextFollowupDate"))
            deadline = parse_date(item.get("deadlineDate"))
            if not matches_scope(
                status=item["status"],
                display_status_value=item["displayStatus"],
                next_followup=next_fu,
                deadline=deadline,
                scope=scope,
                today=today,
            ):
                continue
            items.append(item)

        items.sort(key=quote_sort_key)
        for it in items:
            it.pop("_urgency", None)
        total = len(items)
        page = items[offset : offset + limit]
        return {
            "items": page,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def notification_summary(self) -> dict[str, Any]:
        today = date.today()
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT status, next_followup_date, deadline_date
                FROM {OPPORTUNITIES_TABLE}
                WHERE UPPER(TRIM(status)) IN ('QUOTED', 'FOLLOWING')
                """
            ).fetchall()
        today_count = 0
        overdue_count = 0
        expiring_count = 0
        for row in rows:
            status = (row["status"] or "").strip().upper()
            if status not in ACTIVE_STATUSES:
                continue
            next_fu = parse_date(row["next_followup_date"])
            deadline = parse_date(row["deadline_date"])
            if next_fu is not None and next_fu == today:
                today_count += 1
            if next_fu is not None and next_fu < today:
                overdue_count += 1
            if deadline is not None:
                days_left = (deadline - today).days
                if 0 <= days_left <= EXPIRING_SOON_DAYS:
                    expiring_count += 1
        pending = today_count + overdue_count + expiring_count
        return {
            "todayCount": today_count,
            "overdueCount": overdue_count,
            "expiringSoonCount": expiring_count,
            "pendingCount": pending,
        }

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        now = now_str()
        today = date.today()
        quote_date = parse_date(data.get("quote_date")) or today
        deadline = parse_date(data.get("deadline_date"))
        interval = max(1, int(data.get("followup_interval_days") or 1))
        override_next = parse_date(data.get("next_followup_date"))
        next_fu = compute_next_followup_date(
            base_day=quote_date,
            interval_days=interval,
            deadline=deadline,
            override=override_next,
        )

        is_new = bool(data.get("is_new_customer"))
        customer_id = (data.get("customer_id") or "").strip()
        customer_name = (data.get("customer_name") or "").strip()
        if not customer_name:
            raise ValueError("客户名称不能为空")
        if not is_new and not customer_id:
            # 允许仅名称；标记为新客户
            is_new = True

        oid = str(uuid.uuid4())
        vid = str(uuid.uuid4())
        quote_no = self._generate_quote_no(today)

        product_name = (data.get("product_name") or "").strip()
        address_text = (data.get("address_text") or "").strip()
        ctns = _opt_int(data.get("ctns"))
        weight_kg = _opt_float(data.get("weight_kg"))
        volume_cbm = _opt_float(data.get("volume_cbm"))
        quoted_amount = _opt_float(data.get("quoted_amount"))
        quoted_currency = (data.get("quoted_currency") or "").strip().upper()
        profit_amount = _opt_float(data.get("profit_amount"))
        profit_currency = (data.get("profit_currency") or "").strip().upper()
        profit_rate = _opt_float(data.get("profit_rate"))

        with self._database.lock:
            self._conn.execute(
                f"""
                INSERT INTO {OPPORTUNITIES_TABLE} (
                    id, quote_no, customer_id, customer_name, is_new_customer,
                    customer_inquiry_no, quote_date, deadline_date,
                    followup_interval_days, next_followup_date, status, owner,
                    product_name, address_text, ctns, weight_kg, volume_cbm,
                    current_quote_version_id, current_quoted_amount,
                    current_quoted_currency, current_profit_amount,
                    current_profit_currency, current_profit_rate,
                    lost_reason, note, converted_shipment_id,
                    converted_shipment_no, converted_time,
                    created_time, updated_time
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    '', ?, '', '', '', ?, ?
                )
                """,
                (
                    oid,
                    quote_no,
                    customer_id,
                    customer_name,
                    1 if is_new else 0,
                    (data.get("customer_inquiry_no") or "").strip(),
                    quote_date.isoformat(),
                    deadline.isoformat() if deadline else "",
                    interval,
                    next_fu,
                    STATUS_QUOTED,
                    (data.get("owner") or "").strip(),
                    product_name,
                    address_text,
                    ctns,
                    weight_kg,
                    volume_cbm,
                    vid,
                    quoted_amount,
                    quoted_currency,
                    profit_amount,
                    profit_currency,
                    profit_rate,
                    (data.get("note") or "").strip(),
                    now,
                    now,
                ),
            )
            self._conn.execute(
                f"""
                INSERT INTO {VERSIONS_TABLE} (
                    id, quote_id, version_no, version_time, change_reason,
                    product_name, address_text, ctns, weight_kg, volume_cbm,
                    quoted_amount, quoted_currency, profit_amount,
                    profit_currency, profit_rate, note,
                    created_time, updated_time
                ) VALUES (
                    ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    vid,
                    oid,
                    now,
                    CHANGE_INITIAL,
                    product_name,
                    address_text,
                    ctns,
                    weight_kg,
                    volume_cbm,
                    quoted_amount,
                    quoted_currency,
                    profit_amount,
                    profit_currency,
                    profit_rate,
                    (data.get("note") or "").strip(),
                    now,
                    now,
                ),
            )
            self._conn.commit()
        item = self.get_by_id(oid)
        if item is None:
            raise RuntimeError("创建报价后读取失败")
        return item

    def update(self, quote_id: str, data: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_by_id(quote_id)
        if existing is None:
            raise KeyError(quote_id)
        sets: list[str] = []
        params: list[Any] = []
        mapping = {
            "customer_id": "customer_id",
            "customer_name": "customer_name",
            "customer_inquiry_no": "customer_inquiry_no",
            "owner": "owner",
            "product_name": "product_name",
            "address_text": "address_text",
            "note": "note",
            "lost_reason": "lost_reason",
        }
        for src, col in mapping.items():
            if src in data and data[src] is not None:
                sets.append(f"{col} = ?")
                params.append(str(data[src]).strip())
        if "is_new_customer" in data and data["is_new_customer"] is not None:
            sets.append("is_new_customer = ?")
            params.append(1 if data["is_new_customer"] else 0)
        if "followup_interval_days" in data and data["followup_interval_days"] is not None:
            sets.append("followup_interval_days = ?")
            params.append(max(1, int(data["followup_interval_days"])))
        if "ctns" in data:
            sets.append("ctns = ?")
            params.append(_opt_int(data["ctns"]))
        if "weight_kg" in data:
            sets.append("weight_kg = ?")
            params.append(_opt_float(data["weight_kg"]))
        if "volume_cbm" in data:
            sets.append("volume_cbm = ?")
            params.append(_opt_float(data["volume_cbm"]))
        if "quote_date" in data and data["quote_date"]:
            qd = parse_date(data["quote_date"])
            if qd:
                sets.append("quote_date = ?")
                params.append(qd.isoformat())
        if "deadline_date" in data:
            dd = parse_date(data["deadline_date"]) if data["deadline_date"] else None
            sets.append("deadline_date = ?")
            params.append(dd.isoformat() if dd else "")
        if "next_followup_date" in data:
            nd = parse_date(data["next_followup_date"]) if data["next_followup_date"] else None
            sets.append("next_followup_date = ?")
            params.append(nd.isoformat() if nd else "")
        if "status" in data and data["status"]:
            st = str(data["status"]).strip().upper()
            sets.append("status = ?")
            params.append(st)
        if not sets:
            return existing
        now = now_str()
        sets.append("updated_time = ?")
        params.append(now)
        params.append(quote_id.strip())
        with self._database.lock:
            self._conn.execute(
                f"UPDATE {OPPORTUNITIES_TABLE} SET {', '.join(sets)} WHERE id = ?",
                params,
            )
            self._conn.commit()
        item = self.get_by_id(quote_id)
        if item is None:
            raise KeyError(quote_id)
        return item

    def _next_version_no(self, quote_id: str) -> int:
        row = self._conn.execute(
            f"""
            SELECT MAX(version_no) AS mx FROM {VERSIONS_TABLE} WHERE quote_id = ?
            """,
            (quote_id,),
        ).fetchone()
        return int(row["mx"] or 0) + 1 if row else 1

    def create_followup(
        self,
        quote_id: str,
        *,
        followup_type: str = "",
        note: str = "",
        next_followup_date: str | None = None,
        adjust_quote: bool = False,
        version: dict[str, Any] | None = None,
        created_by: str = "",
    ) -> dict[str, Any]:
        existing = self.get_by_id(quote_id)
        if existing is None:
            raise KeyError(quote_id)
        now = now_str()
        today = date.today()
        sid = quote_id.strip()
        interval = int(existing.get("followupIntervalDays") or 1)
        deadline = parse_date(existing.get("deadlineDate"))
        override = parse_date(next_followup_date) if next_followup_date else None
        computed_next = compute_next_followup_date(
            base_day=today,
            interval_days=interval,
            deadline=deadline,
            override=override,
        )
        version_id = ""
        with self._database.lock:
            if adjust_quote:
                ver = version or {}
                reason = (ver.get("change_reason") or CHANGE_INITIAL).strip().upper()
                if reason not in CHANGE_REASONS or reason == CHANGE_INITIAL:
                    reason = "OTHER"
                version_id = str(uuid.uuid4())
                vno = self._next_version_no(sid)
                product_name = (ver.get("product_name") or existing.get("productName") or "").strip()
                address_text = (ver.get("address_text") or existing.get("addressText") or "").strip()
                ctns = (
                    _opt_int(ver.get("ctns"))
                    if "ctns" in ver
                    else existing.get("ctns")
                )
                weight_kg = (
                    _opt_float(ver.get("weight_kg"))
                    if "weight_kg" in ver
                    else existing.get("weightKg")
                )
                volume_cbm = (
                    _opt_float(ver.get("volume_cbm"))
                    if "volume_cbm" in ver
                    else existing.get("volumeCbm")
                )
                quoted_amount = (
                    _opt_float(ver.get("quoted_amount"))
                    if "quoted_amount" in ver
                    else existing.get("currentQuotedAmount")
                )
                quoted_currency = (
                    (ver.get("quoted_currency") or existing.get("currentQuotedCurrency") or "")
                    .strip()
                    .upper()
                )
                profit_amount = (
                    _opt_float(ver.get("profit_amount"))
                    if "profit_amount" in ver
                    else existing.get("currentProfitAmount")
                )
                profit_currency = (
                    (ver.get("profit_currency") or existing.get("currentProfitCurrency") or "")
                    .strip()
                    .upper()
                )
                profit_rate = (
                    _opt_float(ver.get("profit_rate"))
                    if "profit_rate" in ver
                    else existing.get("currentProfitRate")
                )
                self._conn.execute(
                    f"""
                    INSERT INTO {VERSIONS_TABLE} (
                        id, quote_id, version_no, version_time, change_reason,
                        product_name, address_text, ctns, weight_kg, volume_cbm,
                        quoted_amount, quoted_currency, profit_amount,
                        profit_currency, profit_rate, note,
                        created_time, updated_time
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        version_id,
                        sid,
                        vno,
                        now,
                        reason,
                        product_name,
                        address_text,
                        ctns,
                        weight_kg,
                        volume_cbm,
                        quoted_amount,
                        quoted_currency,
                        profit_amount,
                        profit_currency,
                        profit_rate,
                        (ver.get("note") or "").strip(),
                        now,
                        now,
                    ),
                )
                self._conn.execute(
                    f"""
                    UPDATE {OPPORTUNITIES_TABLE}
                    SET current_quote_version_id = ?,
                        current_quoted_amount = ?,
                        current_quoted_currency = ?,
                        current_profit_amount = ?,
                        current_profit_currency = ?,
                        current_profit_rate = ?,
                        product_name = ?,
                        address_text = ?,
                        ctns = ?,
                        weight_kg = ?,
                        volume_cbm = ?,
                        updated_time = ?
                    WHERE id = ?
                    """,
                    (
                        version_id,
                        quoted_amount,
                        quoted_currency,
                        profit_amount,
                        profit_currency,
                        profit_rate,
                        product_name,
                        address_text,
                        ctns,
                        weight_kg,
                        volume_cbm,
                        now,
                        sid,
                    ),
                )

            fid = str(uuid.uuid4())
            self._conn.execute(
                f"""
                INSERT INTO {FOLLOWUPS_TABLE} (
                    id, quote_id, quote_version_id, followup_time, followup_type,
                    note, next_followup_date, created_by, created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fid,
                    sid,
                    version_id,
                    now,
                    (followup_type or "").strip().lower(),
                    (note or "").strip(),
                    computed_next,
                    (created_by or "").strip(),
                    now,
                    now,
                ),
            )
            new_status = existing.get("status") or STATUS_QUOTED
            if new_status == STATUS_QUOTED:
                new_status = STATUS_FOLLOWING
            self._conn.execute(
                f"""
                UPDATE {OPPORTUNITIES_TABLE}
                SET next_followup_date = ?, status = ?, updated_time = ?
                WHERE id = ?
                """,
                (computed_next, new_status, now, sid),
            )
            self._conn.commit()
            row = self._conn.execute(
                f"SELECT * FROM {FOLLOWUPS_TABLE} WHERE id = ?",
                (fid,),
            ).fetchone()
        if row is None:
            raise RuntimeError("跟进记录写入失败")
        return self._followup_to_api(row)

    def list_versions(self, quote_id: str) -> list[dict[str, Any]]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {VERSIONS_TABLE}
                WHERE quote_id = ?
                ORDER BY version_no DESC
                """,
                (quote_id.strip(),),
            ).fetchall()
        return [self._version_to_api(r) for r in rows]

    def list_followups(self, quote_id: str) -> list[dict[str, Any]]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {FOLLOWUPS_TABLE}
                WHERE quote_id = ?
                ORDER BY datetime(followup_time) DESC, created_time DESC
                """,
                (quote_id.strip(),),
            ).fetchall()
        return [self._followup_to_api(r) for r in rows]

    def mark_won(self, quote_id: str) -> dict[str, Any]:
        return self.update(quote_id, {"status": STATUS_WON, "next_followup_date": ""})

    def mark_lost(
        self,
        quote_id: str,
        *,
        lost_reason: str = "",
        note: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": STATUS_LOST,
            "lost_reason": lost_reason,
            "next_followup_date": "",
        }
        if note is not None:
            payload["note"] = note
        return self.update(quote_id, payload)

    def cancel(self, quote_id: str) -> dict[str, Any]:
        return self.update(
            quote_id, {"status": STATUS_CANCELLED, "next_followup_date": ""}
        )

    def extend_deadline(
        self,
        quote_id: str,
        *,
        deadline_date: str,
        next_followup_date: str | None = None,
    ) -> dict[str, Any]:
        dd = parse_date(deadline_date)
        if not dd:
            raise ValueError("截止日期无效")
        payload: dict[str, Any] = {
            "deadline_date": dd.isoformat(),
            "status": STATUS_FOLLOWING,
        }
        if next_followup_date is not None:
            payload["next_followup_date"] = next_followup_date
        else:
            existing = self.get_by_id(quote_id)
            if existing is None:
                raise KeyError(quote_id)
            interval = int(existing.get("followupIntervalDays") or 1)
            payload["next_followup_date"] = compute_next_followup_date(
                base_day=date.today(),
                interval_days=interval,
                deadline=dd,
            )
        return self.update(quote_id, payload)
