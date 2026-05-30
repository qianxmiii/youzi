"""异常事件持续时间计算与展示。"""

from __future__ import annotations

import calendar
from datetime import datetime

from .datetime_util import DATETIME_FMT, now_str


def _parse_dt(text: str) -> datetime | None:
    raw = (text or "").strip()
    if not raw:
        return None
    for fmt in (DATETIME_FMT, "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _months_days_between(start: datetime, end: datetime) -> tuple[int, int]:
    if end <= start:
        return 0, 0
    months = 0
    while _add_months(start, months + 1) <= end:
        months += 1
    anchor = _add_months(start, months)
    days = (end.date() - anchor.date()).days
    return months, max(0, days)


def _format_months_days(months: int, days: int) -> str:
    if months <= 0:
        if days <= 0:
            return "不足1天"
        return f"{days}天"
    if days > 0:
        return f"{months}月{days}天"
    return f"{months}月"


def duration_seconds(opened_time: str, closed_time: str | None = None) -> int | None:
    start = _parse_dt(opened_time)
    if start is None:
        return None
    end = _parse_dt(closed_time) if closed_time else _parse_dt(now_str())
    if end is None:
        return None
    return max(0, int((end - start).total_seconds()))


def format_duration(
    seconds: int | None,
    *,
    opened_time: str | None = None,
    closed_time: str | None = None,
) -> str:
    if opened_time:
        start = _parse_dt(opened_time)
        end = _parse_dt(closed_time) if closed_time else _parse_dt(now_str())
        if start and end:
            months, days = _months_days_between(start, end)
            return _format_months_days(months, days)
    if seconds is None:
        return "—"
    total_days = max(0, seconds // 86400)
    if total_days >= 30:
        return _format_months_days(total_days // 30, total_days % 30)
    if total_days > 0:
        return _format_months_days(0, total_days)
    return "不足1天" if seconds > 0 else "—"
