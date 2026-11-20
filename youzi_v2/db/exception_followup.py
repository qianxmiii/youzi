"""标记异常运单的跟进提醒间隔（默认每七个自然日）。"""

from __future__ import annotations

from datetime import datetime

from .exception_duration import _parse_dt

# 兼容旧导入名称，所有阶段统一为七天
FOLLOWUP_TIER_UNDER_10_DAYS = 7
FOLLOWUP_TIER_FROM_10_DAYS = 7
FOLLOWUP_TIER_FROM_20_DAYS = 7


def exception_days_open(opened_time: str, *, now: datetime | None = None) -> int:
    """异常已持续的自然日数（含当天）。"""
    start = _parse_dt(opened_time)
    if start is None:
        return 0
    end = now or datetime.now()
    return max(0, (end.date() - start.date()).days)


def followup_interval_days(days_open: int) -> int:
    return 7


def followup_severity(days_open: int) -> str:
    if days_open >= 20:
        return "urgent"
    if days_open >= 10:
        return "warning"
    return "info"


def days_since_anchor(anchor_time: str, *, now: datetime | None = None) -> int | None:
    anchor = _parse_dt(anchor_time)
    if anchor is None:
        return None
    end = now or datetime.now()
    return max(0, (end.date() - anchor.date()).days)


def is_followup_due(
    opened_time: str,
    last_followup_anchor: str | None,
    *,
    now: datetime | None = None,
) -> tuple[bool, int, int]:
    """
    是否应生成跟进提醒。
    last_followup_anchor：上次提醒触发或「已跟进」时间；无则从异常开始时间计。
    返回 (due, days_open, interval_days)。
    """
    now = now or datetime.now()
    days_open = exception_days_open(opened_time, now=now)
    interval = followup_interval_days(days_open)
    anchor = (last_followup_anchor or "").strip() or opened_time
    since = days_since_anchor(anchor, now=now)
    if since is None:
        since = days_open
    return since >= interval, days_open, interval
