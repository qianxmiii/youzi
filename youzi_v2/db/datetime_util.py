"""业务时间字符串：统一 YYYY-MM-DD HH:mm:ss。"""

from __future__ import annotations

from datetime import datetime

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def now_str() -> str:
    return datetime.now().strftime(DATETIME_FMT)


def format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime(DATETIME_FMT)
