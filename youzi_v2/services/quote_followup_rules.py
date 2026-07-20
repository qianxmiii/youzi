"""报价跟进：状态、范围与下次跟进日计算。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..db.shipment_sla import parse_date

STATUS_QUOTED = "QUOTED"
STATUS_FOLLOWING = "FOLLOWING"
STATUS_WON = "WON"
STATUS_LOST = "LOST"
STATUS_EXPIRED = "EXPIRED"
STATUS_CANCELLED = "CANCELLED"

ACTIVE_STATUSES = frozenset({STATUS_QUOTED, STATUS_FOLLOWING})
STOPPED_STATUSES = frozenset(
    {STATUS_WON, STATUS_LOST, STATUS_EXPIRED, STATUS_CANCELLED}
)

STATUS_LABELS: dict[str, str] = {
    STATUS_QUOTED: "已报价",
    STATUS_FOLLOWING: "跟进中",
    STATUS_WON: "已成单",
    STATUS_LOST: "已丢单",
    STATUS_EXPIRED: "已过期",
    STATUS_CANCELLED: "已取消",
}

CHANGE_INITIAL = "INITIAL"
CHANGE_PRICE_DOWN = "PRICE_DOWN"
CHANGE_PRICE_UP = "PRICE_UP"
CHANGE_CARGO = "CARGO_CHANGE"
CHANGE_ADDRESS = "ADDRESS_CHANGE"
CHANGE_CHANNEL = "CHANNEL_CHANGE"
CHANGE_OTHER = "OTHER"

CHANGE_REASON_LABELS: dict[str, str] = {
    CHANGE_INITIAL: "初次报价",
    CHANGE_PRICE_DOWN: "降价",
    CHANGE_PRICE_UP: "涨价",
    CHANGE_CARGO: "修改货物",
    CHANGE_ADDRESS: "修改地址",
    CHANGE_CHANNEL: "修改渠道",
    CHANGE_OTHER: "其他",
}

CHANGE_REASONS = frozenset(CHANGE_REASON_LABELS)

FOLLOWUP_TYPES = frozenset({"phone", "wechat", "email", "other"})
FOLLOWUP_TYPE_LABELS: dict[str, str] = {
    "phone": "电话",
    "wechat": "微信",
    "email": "邮件",
    "other": "其他",
}

SCOPE_TODO = "todo"
SCOPE_TODAY = "today"
SCOPE_OVERDUE_FOLLOWUP = "overdue_followup"
SCOPE_EXPIRING_SOON = "expiring_soon"
SCOPE_EXPIRED = "expired"
SCOPE_ALL_ACTIVE = "all_active"
SCOPE_WON = "won"
SCOPE_LOST = "lost"
SCOPE_CANCELLED = "cancelled"

EXPIRING_SOON_DAYS = 3


def status_label(status: str | None) -> str:
    key = (status or "").strip().upper()
    return STATUS_LABELS.get(key, key or "—")


def change_reason_label(reason: str | None) -> str:
    key = (reason or "").strip().upper()
    return CHANGE_REASON_LABELS.get(key, key or "—")


def followup_type_label(value: str | None) -> str:
    key = (value or "").strip().lower()
    return FOLLOWUP_TYPE_LABELS.get(key, key or "—")


def _date_str(d: date | None) -> str:
    return d.isoformat() if d else ""


def add_days(base: date, days: int) -> date:
    return base + timedelta(days=max(0, int(days)))


def compute_next_followup_date(
    *,
    base_day: date,
    interval_days: int,
    deadline: date | None,
    override: date | None = None,
) -> str:
    """计算下次跟进日；若超过有效期则返回空字符串（不再提醒）。"""
    if override is not None:
        nxt = override
    else:
        nxt = add_days(base_day, interval_days)
    if deadline is not None and nxt > deadline:
        return ""
    return _date_str(nxt)


def display_status(row_status: str | None, deadline: date | None, today: date) -> str:
    """列表展示状态：库内非终态且已过有效期时显示为已过期（不改库）。"""
    st = (row_status or "").strip().upper() or STATUS_QUOTED
    if st in STOPPED_STATUSES:
        return st
    if deadline is not None and today > deadline:
        return STATUS_EXPIRED
    return st


def classify_urgency(
    *,
    status: str,
    next_followup: date | None,
    deadline: date | None,
    today: date,
) -> str:
    """用于排序：overdue_followup / today / expiring_soon / other。"""
    st = (status or "").strip().upper()
    if st not in ACTIVE_STATUSES:
        return "other"
    if next_followup is not None and next_followup < today:
        return "overdue_followup"
    if next_followup is not None and next_followup == today:
        return "today"
    if deadline is not None:
        days_left = (deadline - today).days
        if 0 <= days_left <= EXPIRING_SOON_DAYS:
            return "expiring_soon"
        if days_left < 0:
            return "expired"
    return "other"


URGENCY_SORT: dict[str, int] = {
    "overdue_followup": 0,
    "today": 1,
    "expiring_soon": 2,
    "expired": 3,
    "other": 4,
}


def matches_scope(
    *,
    status: str,
    display_status_value: str,
    next_followup: date | None,
    deadline: date | None,
    scope: str,
    today: date,
) -> bool:
    sc = (scope or SCOPE_TODO).strip().lower()
    st = (status or "").strip().upper()
    disp = (display_status_value or st).strip().upper()

    if sc == SCOPE_WON:
        return st == STATUS_WON
    if sc == SCOPE_LOST:
        return st == STATUS_LOST
    if sc == SCOPE_CANCELLED:
        return st == STATUS_CANCELLED
    if sc == SCOPE_EXPIRED:
        return disp == STATUS_EXPIRED or st == STATUS_EXPIRED
    if sc == SCOPE_ALL_ACTIVE:
        return st in ACTIVE_STATUSES

    if st not in ACTIVE_STATUSES:
        return False

    overdue = next_followup is not None and next_followup < today
    today_due = next_followup is not None and next_followup == today
    expired = deadline is not None and today > deadline
    expiring = False
    if deadline is not None and not expired:
        expiring = 0 <= (deadline - today).days <= EXPIRING_SOON_DAYS

    if sc == SCOPE_TODAY:
        return today_due
    if sc == SCOPE_OVERDUE_FOLLOWUP:
        return overdue
    if sc == SCOPE_EXPIRING_SOON:
        return expiring
    if sc == SCOPE_TODO:
        return overdue or today_due or expiring or expired
    return True


def quote_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    urgency = item.get("_urgency") or "other"
    order = URGENCY_SORT.get(str(urgency), 99)
    next_fu = item.get("nextFollowupDate") or "9999-99-99"
    deadline = item.get("deadlineDate") or "9999-99-99"
    return (order, next_fu, deadline, item.get("quoteNo") or "")
