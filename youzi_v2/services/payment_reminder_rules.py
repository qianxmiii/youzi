"""催款列表：结算方式与应催日期计算。"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from ..db.shipment_sla import parse_date

SETTLEMENT_BEFORE_SHIPMENT = "BEFORE_SHIPMENT"
SETTLEMENT_BEFORE_ARRIVAL = "BEFORE_ARRIVAL"
SETTLEMENT_AFTER_ARRIVAL = "AFTER_ARRIVAL"
SETTLEMENT_MONTHLY = "MONTHLY"
SETTLEMENT_AFTER_DELIVERY = "AFTER_DELIVERY"

SETTLEMENT_METHODS = frozenset(
    {
        SETTLEMENT_BEFORE_SHIPMENT,
        SETTLEMENT_BEFORE_ARRIVAL,
        SETTLEMENT_AFTER_ARRIVAL,
        SETTLEMENT_MONTHLY,
        SETTLEMENT_AFTER_DELIVERY,
    }
)

SETTLEMENT_LABELS: dict[str, str] = {
    SETTLEMENT_BEFORE_SHIPMENT: "发货前结",
    SETTLEMENT_BEFORE_ARRIVAL: "到港前结",
    SETTLEMENT_AFTER_ARRIVAL: "到港后结",
    SETTLEMENT_MONTHLY: "月结",
    SETTLEMENT_AFTER_DELIVERY: "签收结",
}

REMINDER_UPCOMING_7 = "upcoming_7_days"
REMINDER_TODAY = "today"
REMINDER_OVERDUE = "overdue"
REMINDER_MONTHLY = "monthly"
REMINDER_MISSING_RULE = "missing_rule"
REMINDER_MISSING_DATE = "missing_date"

REMINDER_TYPE_LABELS: dict[str, str] = {
    REMINDER_UPCOMING_7: "提前7天",
    REMINDER_TODAY: "当天",
    REMINDER_OVERDUE: "已逾期",
    REMINDER_MONTHLY: "月结",
    REMINDER_MISSING_RULE: "未设置结算方式",
    REMINDER_MISSING_DATE: "缺少时间字段",
}

REMINDER_SORT_ORDER: dict[str, int] = {
    REMINDER_OVERDUE: 0,
    REMINDER_TODAY: 1,
    REMINDER_MONTHLY: 2,
    REMINDER_UPCOMING_7: 3,
    REMINDER_MISSING_RULE: 4,
    REMINDER_MISSING_DATE: 5,
}

SCOPE_TODO = "todo"
SCOPE_ALL_UNPAID = "all_unpaid"

# 常规应付款日逾期超过该天数后，改用签收日计算逾期天数（非结算口径）
LONG_OVERDUE_USE_DELIVERY_DAYS = 15


def settlement_method_label(method: str | None) -> str:
    key = (method or "").strip().upper()
    if not key:
        return "未设置"
    return SETTLEMENT_LABELS.get(key, key)


def reminder_type_label(reminder_type: str | None) -> str:
    key = (reminder_type or "").strip()
    return REMINDER_TYPE_LABELS.get(key, key or "—")


def is_unpaid_payment_status(value: str | None) -> bool:
    return (value or "").strip().upper() != "PAID"


def monthly_due_date(entry_day: date, settlement_day: int) -> date:
    if entry_day.month == 12:
        year, month = entry_day.year + 1, 1
    else:
        year, month = entry_day.year, entry_day.month + 1
    last_day = monthrange(year, month)[1]
    day = min(max(1, settlement_day), last_day)
    return date(year, month, day)


def _date_str(d: date | None) -> str:
    return d.isoformat() if d else ""


def _base_result(
    *,
    settlement_method: str | None,
    base_date_field: str,
    base_date: date | None,
    due_date: date | None,
    reminder_date: date | None,
    reminder_type: str,
    today: date,
) -> dict[str, Any]:
    due = due_date
    days_until: int | None = None
    overdue_days = 0
    rt = (reminder_type or "").strip()
    if due is not None:
        delta = (due - today).days
        if rt == REMINDER_OVERDUE:
            overdue_days = abs(delta) if delta < 0 else 0
        elif rt in (REMINDER_TODAY, REMINDER_MONTHLY):
            days_until = 0
        elif rt == REMINDER_UPCOMING_7:
            days_until = max(0, delta)
        elif not rt:
            days_until = max(0, delta) if delta >= 0 else None
    return {
        "settlementMethod": (settlement_method or "").strip().upper() or None,
        "settlementMethodLabel": settlement_method_label(settlement_method),
        "baseDateField": base_date_field,
        "baseDate": _date_str(base_date),
        "dueDate": _date_str(due),
        "reminderDate": _date_str(reminder_date),
        "reminderType": reminder_type,
        "reminderTypeLabel": reminder_type_label(reminder_type),
        "daysUntilDue": days_until if days_until is not None else 0,
        "overdueDays": overdue_days,
    }


def _adjust_long_overdue_days(
    result: dict[str, Any],
    row: dict[str, Any],
    today: date,
) -> dict[str, Any]:
    """常规逾期超过 15 天时，按签收时间重算逾期天数。"""
    rt = (result.get("reminderType") or "").strip()
    if rt != REMINDER_OVERDUE:
        return result
    regular_overdue = int(result.get("overdueDays") or 0)
    if regular_overdue <= LONG_OVERDUE_USE_DELIVERY_DAYS:
        return result
    delivered = parse_date(row.get("delivered_time"))
    if not delivered:
        return result
    delivery_overdue = (today - delivered).days
    if delivery_overdue < 0:
        delivery_overdue = 0
    return {**result, "overdueDays": delivery_overdue}


def _windowed_reminder(
    *,
    settlement_method: str,
    base_date_field: str,
    anchor: date,
    today: date,
    advance_days: int = 7,
) -> dict[str, Any]:
    reminder_start = anchor - timedelta(days=advance_days)
    due_date = anchor
    if today < reminder_start:
        reminder_type = ""
    elif today < anchor:
        reminder_type = REMINDER_UPCOMING_7
    elif today == anchor:
        reminder_type = REMINDER_TODAY
    else:
        reminder_type = REMINDER_OVERDUE
    return _base_result(
        settlement_method=settlement_method,
        base_date_field=base_date_field,
        base_date=anchor,
        due_date=due_date,
        reminder_date=reminder_start if advance_days else anchor,
        reminder_type=reminder_type,
        today=today,
    )


def _compute_payment_reminder_inner(
    row: dict[str, Any],
    *,
    settlement_method: str | None,
    settlement_day: int | None,
    today: date | None = None,
) -> dict[str, Any]:
    check_day = today or date.today()
    method = (settlement_method or "").strip().upper()

    if not method or method not in SETTLEMENT_METHODS:
        return _base_result(
            settlement_method=None,
            base_date_field="",
            base_date=None,
            due_date=None,
            reminder_date=None,
            reminder_type=REMINDER_MISSING_RULE,
            today=check_day,
        )

    if method == SETTLEMENT_BEFORE_SHIPMENT:
        anchor = parse_date(row.get("etd"))
        if not anchor:
            return _base_result(
                settlement_method=method,
                base_date_field="etd",
                base_date=None,
                due_date=None,
                reminder_date=None,
                reminder_type=REMINDER_MISSING_DATE,
                today=check_day,
            )
        return _windowed_reminder(
            settlement_method=method,
            base_date_field="etd",
            anchor=anchor,
            today=check_day,
        )

    if method == SETTLEMENT_BEFORE_ARRIVAL:
        eta = parse_date(row.get("eta"))
        ata = parse_date(row.get("ata"))
        if not eta:
            return _base_result(
                settlement_method=method,
                base_date_field="eta",
                base_date=None,
                due_date=None,
                reminder_date=None,
                reminder_type=REMINDER_MISSING_DATE,
                today=check_day,
            )
        reminder_start = eta - timedelta(days=7)
        if ata and check_day >= ata:
            if check_day > eta:
                reminder_type = REMINDER_OVERDUE
            elif check_day == eta:
                reminder_type = REMINDER_TODAY
            else:
                reminder_type = REMINDER_OVERDUE
            return _base_result(
                settlement_method=method,
                base_date_field="eta",
                base_date=eta,
                due_date=eta,
                reminder_date=reminder_start,
                reminder_type=reminder_type,
                today=check_day,
            )
        if check_day > eta:
            return _base_result(
                settlement_method=method,
                base_date_field="eta",
                base_date=eta,
                due_date=eta,
                reminder_date=reminder_start,
                reminder_type=REMINDER_OVERDUE,
                today=check_day,
            )
        return _windowed_reminder(
            settlement_method=method,
            base_date_field="eta",
            anchor=eta,
            today=check_day,
        )

    if method == SETTLEMENT_AFTER_ARRIVAL:
        anchor = parse_date(row.get("ata"))
        if not anchor:
            return _base_result(
                settlement_method=method,
                base_date_field="ata",
                base_date=None,
                due_date=None,
                reminder_date=None,
                reminder_type=REMINDER_MISSING_DATE,
                today=check_day,
            )
        if check_day < anchor:
            return _base_result(
                settlement_method=method,
                base_date_field="ata",
                base_date=anchor,
                due_date=anchor,
                reminder_date=anchor,
                reminder_type="",
                today=check_day,
            )
        if check_day == anchor:
            reminder_type = REMINDER_TODAY
        else:
            reminder_type = REMINDER_OVERDUE
        return _base_result(
            settlement_method=method,
            base_date_field="ata",
            base_date=anchor,
            due_date=anchor,
            reminder_date=anchor,
            reminder_type=reminder_type,
            today=check_day,
        )

    if method == SETTLEMENT_MONTHLY:
        entry = parse_date(row.get("warehouse_entry_time"))
        if not entry:
            return _base_result(
                settlement_method=method,
                base_date_field="warehouse_entry_time",
                base_date=None,
                due_date=None,
                reminder_date=None,
                reminder_type=REMINDER_MISSING_DATE,
                today=check_day,
            )
        day_no = settlement_day
        if day_no is None or day_no < 1 or day_no > 31:
            return _base_result(
                settlement_method=method,
                base_date_field="warehouse_entry_time",
                base_date=entry,
                due_date=None,
                reminder_date=None,
                reminder_type=REMINDER_MISSING_RULE,
                today=check_day,
            )
        due = monthly_due_date(entry, int(day_no))
        if check_day < due:
            return _base_result(
                settlement_method=method,
                base_date_field="warehouse_entry_time",
                base_date=entry,
                due_date=due,
                reminder_date=due,
                reminder_type="",
                today=check_day,
            )
        if check_day == due:
            reminder_type = REMINDER_MONTHLY
        else:
            reminder_type = REMINDER_OVERDUE
        return _base_result(
            settlement_method=method,
            base_date_field="warehouse_entry_time",
            base_date=entry,
            due_date=due,
            reminder_date=due,
            reminder_type=reminder_type,
            today=check_day,
        )

    if method == SETTLEMENT_AFTER_DELIVERY:
        anchor = parse_date(row.get("delivered_time"))
        if not anchor:
            return _base_result(
                settlement_method=method,
                base_date_field="delivered_time",
                base_date=None,
                due_date=None,
                reminder_date=None,
                reminder_type=REMINDER_MISSING_DATE,
                today=check_day,
            )
        if check_day < anchor:
            return _base_result(
                settlement_method=method,
                base_date_field="delivered_time",
                base_date=anchor,
                due_date=anchor,
                reminder_date=anchor,
                reminder_type="",
                today=check_day,
            )
        if check_day == anchor:
            reminder_type = REMINDER_TODAY
        else:
            reminder_type = REMINDER_OVERDUE
        return _base_result(
            settlement_method=method,
            base_date_field="delivered_time",
            base_date=anchor,
            due_date=anchor,
            reminder_date=anchor,
            reminder_type=reminder_type,
            today=check_day,
        )

    return _base_result(
        settlement_method=None,
        base_date_field="",
        base_date=None,
        due_date=None,
        reminder_date=None,
        reminder_type=REMINDER_MISSING_RULE,
        today=check_day,
    )


def compute_payment_reminder(
    row: dict[str, Any],
    *,
    settlement_method: str | None,
    settlement_day: int | None,
    today: date | None = None,
) -> dict[str, Any]:
    """根据运单与客户结算配置计算催款上下文。"""
    check_day = today or date.today()
    result = _compute_payment_reminder_inner(
        row,
        settlement_method=settlement_method,
        settlement_day=settlement_day,
        today=check_day,
    )
    return _adjust_long_overdue_days(result, row, check_day)


def matches_scope(reminder_type: str, scope: str) -> bool:
    rt = (reminder_type or "").strip()
    sc = (scope or SCOPE_TODO).strip().lower()
    if sc == SCOPE_ALL_UNPAID:
        return True
    if sc == REMINDER_MISSING_RULE:
        return rt == REMINDER_MISSING_RULE
    if sc == REMINDER_MISSING_DATE:
        return rt == REMINDER_MISSING_DATE
    if sc == REMINDER_UPCOMING_7:
        return rt == REMINDER_UPCOMING_7
    if sc == REMINDER_TODAY:
        return rt in (REMINDER_TODAY, REMINDER_MONTHLY)
    if sc == REMINDER_OVERDUE:
        return rt == REMINDER_OVERDUE
    if sc == SCOPE_TODO:
        return rt in (
            REMINDER_UPCOMING_7,
            REMINDER_TODAY,
            REMINDER_OVERDUE,
            REMINDER_MONTHLY,
            REMINDER_MISSING_RULE,
        )
    return False


def reminder_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    rt = (item.get("reminderType") or "").strip()
    order = REMINDER_SORT_ORDER.get(rt, 99)
    due = item.get("dueDate") or "9999-99-99"
    return (order, due, item.get("shipmentNo") or "")
