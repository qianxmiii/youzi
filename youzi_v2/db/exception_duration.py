"""异常事件持续时间计算与展示。"""

from __future__ import annotations

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


def _format_days(days: int, *, has_subday_elapsed: bool = False) -> str:
    if days <= 0:
        return "不足1天" if has_subday_elapsed else "—"
    return f"{days}天"


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
            days = max(0, (end.date() - start.date()).days)
            subday = days <= 0 and end > start
            return _format_days(days, has_subday_elapsed=subday)
    if seconds is None:
        return "—"
    total_days = max(0, seconds // 86400)
    return _format_days(total_days, has_subday_elapsed=seconds > 0 and total_days <= 0)
