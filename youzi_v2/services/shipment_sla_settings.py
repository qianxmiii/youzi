"""运输时效预警扫描计划任务配置。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..db.app_settings_table import get_setting, set_setting
from ..db.connection import Database
from ..db.datetime_util import now_str
from .scheduled_sync_settings import _parse_bool

KEY_SLA_SCAN_ENABLED = "sla.scan.enabled"
KEY_SLA_SCAN_LAST_FINISHED = "sla.scan.last_finished_at"

SLA_SCAN_INTERVAL_HOURS = 24.0


@dataclass(frozen=True)
class ShipmentSlaScanSettings:
    enabled: bool
    last_finished: str | None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "slaScanEnabled": self.enabled,
            "slaScanLastFinished": self.last_finished,
        }


def ensure_sla_scan_defaults(conn) -> None:
    if get_setting(conn, KEY_SLA_SCAN_ENABLED) is None:
        set_setting(conn, KEY_SLA_SCAN_ENABLED, "1")


def get_sla_scan_settings(database: Database) -> ShipmentSlaScanSettings:
    with database.lock:
        ensure_sla_scan_defaults(database.conn)
        enabled = _parse_bool(get_setting(database.conn, KEY_SLA_SCAN_ENABLED), True)
        last_finished = get_setting(database.conn, KEY_SLA_SCAN_LAST_FINISHED)
    return ShipmentSlaScanSettings(enabled=enabled, last_finished=last_finished)


def save_sla_scan_enabled(database: Database, *, enabled: bool) -> ShipmentSlaScanSettings:
    with database.lock:
        ensure_sla_scan_defaults(database.conn)
        set_setting(database.conn, KEY_SLA_SCAN_ENABLED, "1" if enabled else "0")
        database.conn.commit()
    return get_sla_scan_settings(database)


def record_sla_scan_finished(database: Database) -> None:
    with database.lock:
        set_setting(database.conn, KEY_SLA_SCAN_LAST_FINISHED, now_str())
        database.conn.commit()
