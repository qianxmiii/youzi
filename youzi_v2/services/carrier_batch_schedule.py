"""承运商全库批处理间隔：与定时任务 YOUZI_TRACKING_SYNC_INTERVAL_HOURS 对齐（默认 2 小时）。"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from ..db.app_settings_table import get_setting, set_setting
from ..db.connection import Database
from ..db.datetime_util import DATETIME_FMT, now_str

SETTING_LAST_CARRIER_BATCH_FINISHED = "tracking.carrier_batch.last_finished_at"


def carrier_batch_interval_hours() -> float:
    return float(os.getenv("YOUZI_TRACKING_SYNC_INTERVAL_HOURS", "2"))


def is_carrier_full_batch(shipment_nos: list[str] | None) -> bool:
    if not shipment_nos:
        return True
    return not any(s and str(s).strip() for s in shipment_nos)


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


def should_run_scheduled_carrier_batch(database: Database) -> tuple[bool, str | None]:
    """
    定时/启动触发的全库承运商同步是否应执行。
    返回 (True, None) 可执行；(False, 原因) 跳过。
    """
    hours = carrier_batch_interval_hours()
    if hours <= 0:
        return True, None

    with database.lock:
        last_raw = get_setting(database.conn, SETTING_LAST_CARRIER_BATCH_FINISHED)

    finished = _parse_finished_at(last_raw)
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
    """全库承运商批处理成功结束后写入完成时间。"""
    with database.lock:
        set_setting(database.conn, SETTING_LAST_CARRIER_BATCH_FINISHED, now_str())
        database.conn.commit()


def get_last_carrier_batch_finished(database: Database) -> str | None:
    with database.lock:
        return get_setting(database.conn, SETTING_LAST_CARRIER_BATCH_FINISHED)
