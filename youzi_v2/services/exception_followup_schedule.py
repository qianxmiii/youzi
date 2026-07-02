"""异常跟进提醒扫描间隔（每天一次，须启用定时开关）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..db.connection import Database
from ..db.datetime_util import DATETIME_FMT
from .exception_followup_settings import EXCEPTION_FOLLOWUP_INTERVAL_HOURS, get_exception_followup_settings


def _parse_finished_at(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip().replace("T", " ")[:19]
    try:
        return datetime.strptime(text, DATETIME_FMT)
    except ValueError:
        return None


def should_run_exception_followup_scan(database: Database) -> tuple[bool, str | None]:
    settings = get_exception_followup_settings(database)
    if not settings.enabled:
        return False, "异常跟进定时扫描已关闭"

    finished = _parse_finished_at(settings.last_finished)
    if finished is None:
        return True, None
    elapsed = datetime.now() - finished
    need = timedelta(hours=EXCEPTION_FOLLOWUP_INTERVAL_HOURS)
    if elapsed < need:
        remain = need - elapsed
        h, rem = divmod(int(remain.total_seconds()), 3600)
        m = rem // 60
        return False, f"距上次扫描不足 24 小时（约 {h}小时{m}分 后可再跑）"
    return True, None
