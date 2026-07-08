"""运输时效预警扫描调度门控。"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..db.connection import Database
from ..db.datetime_util import DATETIME_FMT
from .shipment_sla_settings import SLA_SCAN_INTERVAL_HOURS, get_sla_scan_settings


def _parse_dt(text: str | None) -> datetime | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, DATETIME_FMT)
    except ValueError:
        return None


def should_run_sla_scan(database: Database) -> tuple[bool, str | None]:
    settings = get_sla_scan_settings(database)
    if not settings.enabled:
        return False, "运输时效扫描已关闭"
    last = _parse_dt(settings.last_finished)
    if last is None:
        return True, None
    if datetime.now() - last >= timedelta(hours=SLA_SCAN_INTERVAL_HOURS):
        return True, None
    return False, "距上次运输时效扫描未满 24 小时"
