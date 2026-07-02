"""邮编回写批处理间隔（每天一次）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..db.connection import Database
from ..db.datetime_util import DATETIME_FMT
from .zipcode_backfill_settings import (
    ZIPCODE_BACKFILL_INTERVAL_HOURS,
    get_zipcode_backfill_settings,
)


def _parse_finished_at(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip().replace("T", " ")[:19]
    try:
        return datetime.strptime(text, DATETIME_FMT)
    except ValueError:
        return None


def _format_duration(delta: timedelta) -> str:
    total_sec = max(0, int(delta.total_seconds()))
    h, rem = divmod(total_sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}小时{m}分"
    if m:
        return f"{m}分{s}秒"
    return f"{s}秒"


def should_run_scheduled_zipcode_backfill(database: Database) -> tuple[bool, str | None]:
    settings = get_zipcode_backfill_settings(database)
    if not settings.enabled:
        return False, "邮编回写已关闭"

    finished = _parse_finished_at(settings.last_finished)
    if finished is None:
        return True, None

    elapsed = datetime.now() - finished
    need = timedelta(hours=ZIPCODE_BACKFILL_INTERVAL_HOURS)
    if elapsed < need:
        remain = need - elapsed
        return (
            False,
            f"距上次邮编回写 {_format_duration(elapsed)}，"
            f"未满 {ZIPCODE_BACKFILL_INTERVAL_HOURS:g} 小时（约 {_format_duration(remain)} 后可执行）",
        )
    return True, None
