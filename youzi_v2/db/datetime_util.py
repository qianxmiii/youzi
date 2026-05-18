"""业务时间字符串：统一 YYYY-MM-DD HH:mm:ss。"""

from __future__ import annotations

import re
from datetime import datetime

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
_RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_DATETIME_MIN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
_RE_DATETIME_SEC = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def now_str() -> str:
    return datetime.now().strftime(DATETIME_FMT)


def format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime(DATETIME_FMT)


def normalize_tracking_time(raw: str | None) -> str:
    """将轨迹时间规范为 YYYY-MM-DD HH:mm:ss；缺秒则补 :00。"""
    text = (raw or "").strip()
    if not text:
        return ""
    if "T" in text:
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt.strftime(DATETIME_FMT)
        except ValueError:
            pass
    if _RE_DATETIME_SEC.match(text):
        return text
    if _RE_DATETIME_MIN.match(text):
        return f"{text}:00"
    if _RE_DATE.match(text):
        return f"{text} 00:00:00"
    return text
