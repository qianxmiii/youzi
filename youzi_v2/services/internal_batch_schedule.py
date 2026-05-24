"""内部轨迹全库批处理间隔（读 app_settings）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..db.connection import Database
from ..db.datetime_util import DATETIME_FMT
from .carrier_batch_schedule import _format_duration, _parse_finished_at
from .scheduled_sync_settings import get_scheduled_sync_settings
from .scheduled_sync_settings import record_internal_batch_finished


def is_internal_full_batch(shipment_nos: list[str] | None) -> bool:
    if not shipment_nos:
        return True
    return not any(s and str(s).strip() for s in shipment_nos)


def should_run_scheduled_internal_batch(database: Database) -> tuple[bool, str | None]:
    settings = get_scheduled_sync_settings(database)
    if not settings.internal_enabled:
        return False, "内部轨迹定时同步已关闭"
    hours = settings.internal_interval_hours
    if hours <= 0:
        return True, None

    finished = _parse_finished_at(settings.last_internal_finished)
    if finished is None:
        return True, None

    elapsed = datetime.now() - finished
    need = timedelta(hours=hours)
    if elapsed < need:
        remain = need - elapsed
        return (
            False,
            f"距上次全库内部同步 {_format_duration(elapsed)}，"
            f"未满 {hours:g} 小时（约 {_format_duration(remain)} 后可执行）",
        )
    return True, None


__all__ = [
    "is_internal_full_batch",
    "record_internal_batch_finished",
    "should_run_scheduled_internal_batch",
]
