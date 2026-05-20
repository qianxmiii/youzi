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


def duration_seconds(opened_time: str, closed_time: str | None = None) -> int | None:
    start = _parse_dt(opened_time)
    if start is None:
        return None
    end = _parse_dt(closed_time) if closed_time else _parse_dt(now_str())
    if end is None:
        return None
    return max(0, int((end - start).total_seconds()))


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds}秒"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}分钟"
    hours = minutes // 60
    if hours < 24:
        rem_m = minutes % 60
        return f"{hours}小时{rem_m}分" if rem_m else f"{hours}小时"
    days = hours // 24
    rem_h = hours % 24
    return f"{days}天{rem_h}小时" if rem_h else f"{days}天"
