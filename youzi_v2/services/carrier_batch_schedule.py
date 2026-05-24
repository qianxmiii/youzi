"""承运商全库批处理间隔（读 app_settings）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..db.app_settings_table import get_setting, set_setting
from ..db.connection import Database
from ..db.datetime_util import DATETIME_FMT, now_str
from .scheduled_sync_settings import (
    SETTING_LAST_CARRIER_BATCH_FINISHED,
    get_scheduled_sync_settings,
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


def carrier_batch_interval_hours(database: Database | None = None) -> float:
    if database is not None:
        return get_scheduled_sync_settings(database).carrier_interval_hours
    from .scheduled_sync_settings import _env_interval_hours

    return max(0.0, _env_interval_hours())


def is_carrier_full_batch(shipment_nos: list[str] | None) -> bool:
    if not shipment_nos:
        return True
    return not any(s and str(s).strip() for s in shipment_nos)


def should_run_scheduled_carrier_batch(database: Database) -> tuple[bool, str | None]:
    settings = get_scheduled_sync_settings(database)
    if not settings.carrier_enabled:
        return False, "承运商轨迹定时同步已关闭"
    hours = settings.carrier_interval_hours
    if hours <= 0:
        return True, None

    finished = _parse_finished_at(settings.last_carrier_finished)
    if finished is None:
        return True, None

    elapsed = datetime.now() - finished
    need = timedelta(hours=hours)
    if elapsed < need:
        remain = need - elapsed
        return (
            False,
            f"距上次全库承运商同步 {_format_duration(elapsed)}，"
            f"未满 {hours:g} 小时（约 {_format_duration(remain)} 后可执行）",
        )
    return True, None


def record_carrier_batch_finished(database: Database) -> None:
    with database.lock:
        set_setting(database.conn, SETTING_LAST_CARRIER_BATCH_FINISHED, now_str())
        database.conn.commit()


def get_last_carrier_batch_finished(database: Database) -> str | None:
    with database.lock:
        return get_setting(database.conn, SETTING_LAST_CARRIER_BATCH_FINISHED)
