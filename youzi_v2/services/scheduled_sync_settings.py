"""计划任务配置（app_settings，页面可改；缺省时回退环境变量）。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from ..db.app_settings_table import get_setting, set_setting
from ..db.connection import Database

KEY_INTERNAL_ENABLED = "tracking.internal.enabled"
KEY_INTERNAL_INTERVAL_HOURS = "tracking.internal.interval_hours"
KEY_INTERNAL_LAST_FINISHED = "tracking.internal.last_finished_at"

KEY_CARRIER_ENABLED = "tracking.carrier.enabled"
KEY_CARRIER_INTERVAL_HOURS = "tracking.carrier.interval_hours"
SETTING_LAST_CARRIER_BATCH_FINISHED = "tracking.carrier_batch.last_finished_at"

KEY_INITIAL_DELAY_SEC = "tracking.scheduler.initial_delay_sec"

DEFAULT_INTERVAL_HOURS = 2.0
DEFAULT_INITIAL_DELAY_SEC = 60.0
MIN_INTERVAL_HOURS = 0.25
MAX_INTERVAL_HOURS = 168.0


def _env_interval_hours() -> float:
    try:
        return float(os.getenv("YOUZI_TRACKING_SYNC_INTERVAL_HOURS", str(DEFAULT_INTERVAL_HOURS)))
    except ValueError:
        return DEFAULT_INTERVAL_HOURS


def _env_initial_delay_sec() -> float:
    try:
        return float(os.getenv("YOUZI_TRACKING_SYNC_INITIAL_DELAY_SEC", str(DEFAULT_INITIAL_DELAY_SEC)))
    except ValueError:
        return DEFAULT_INITIAL_DELAY_SEC


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _parse_float(raw: str | None, default: float) -> float:
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


def _clamp_interval(hours: float) -> float:
    return max(MIN_INTERVAL_HOURS, min(MAX_INTERVAL_HOURS, hours))


@dataclass(frozen=True)
class ScheduledSyncSettings:
    internal_enabled: bool
    internal_interval_hours: float
    carrier_enabled: bool
    carrier_interval_hours: float
    initial_delay_sec: float
    last_internal_finished: str | None
    last_carrier_finished: str | None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "internalEnabled": self.internal_enabled,
            "internalIntervalHours": self.internal_interval_hours,
            "carrierEnabled": self.carrier_enabled,
            "carrierIntervalHours": self.carrier_interval_hours,
            "initialDelaySec": self.initial_delay_sec,
            "lastInternalFinished": self.last_internal_finished,
            "lastCarrierFinished": self.last_carrier_finished,
            "schedulerActive": self.internal_enabled or self.carrier_enabled,
        }


def ensure_scheduled_sync_defaults(conn) -> None:
    env_hours = _env_interval_hours()
    env_on = env_hours > 0
    defaults: list[tuple[str, str]] = [
        (KEY_INTERNAL_ENABLED, "1" if env_on else "0"),
        (KEY_INTERNAL_INTERVAL_HOURS, str(env_hours if env_hours > 0 else DEFAULT_INTERVAL_HOURS)),
        (KEY_CARRIER_ENABLED, "1" if env_on else "0"),
        (KEY_CARRIER_INTERVAL_HOURS, str(env_hours if env_hours > 0 else DEFAULT_INTERVAL_HOURS)),
        (KEY_INITIAL_DELAY_SEC, str(_env_initial_delay_sec())),
    ]
    for key, value in defaults:
        if get_setting(conn, key) is None:
            set_setting(conn, key, value)


def get_scheduled_sync_settings(database: Database) -> ScheduledSyncSettings:
    with database.lock:
        ensure_scheduled_sync_defaults(database.conn)
        env_hours = _env_interval_hours()
        env_on = env_hours > 0
        internal_enabled = _parse_bool(
            get_setting(database.conn, KEY_INTERNAL_ENABLED),
            env_on,
        )
        carrier_enabled = _parse_bool(
            get_setting(database.conn, KEY_CARRIER_ENABLED),
            env_on,
        )
        internal_interval = _clamp_interval(
            _parse_float(
                get_setting(database.conn, KEY_INTERNAL_INTERVAL_HOURS),
                env_hours if env_hours > 0 else DEFAULT_INTERVAL_HOURS,
            )
        )
        carrier_interval = _clamp_interval(
            _parse_float(
                get_setting(database.conn, KEY_CARRIER_INTERVAL_HOURS),
                env_hours if env_hours > 0 else DEFAULT_INTERVAL_HOURS,
            )
        )
        initial_delay = max(
            0.0,
            _parse_float(
                get_setting(database.conn, KEY_INITIAL_DELAY_SEC),
                _env_initial_delay_sec(),
            ),
        )
        last_internal = get_setting(database.conn, KEY_INTERNAL_LAST_FINISHED)
        last_carrier = get_setting(database.conn, SETTING_LAST_CARRIER_BATCH_FINISHED)

    return ScheduledSyncSettings(
        internal_enabled=internal_enabled,
        internal_interval_hours=internal_interval,
        carrier_enabled=carrier_enabled,
        carrier_interval_hours=carrier_interval,
        initial_delay_sec=initial_delay,
        last_internal_finished=last_internal,
        last_carrier_finished=last_carrier,
    )


def save_scheduled_sync_settings(
    database: Database,
    *,
    internal_enabled: bool,
    internal_interval_hours: float,
    carrier_enabled: bool,
    carrier_interval_hours: float,
    initial_delay_sec: float,
) -> ScheduledSyncSettings:
    with database.lock:
        ensure_scheduled_sync_defaults(database.conn)
        set_setting(database.conn, KEY_INTERNAL_ENABLED, "1" if internal_enabled else "0")
        set_setting(
            database.conn,
            KEY_INTERNAL_INTERVAL_HOURS,
            str(_clamp_interval(internal_interval_hours)),
        )
        set_setting(database.conn, KEY_CARRIER_ENABLED, "1" if carrier_enabled else "0")
        set_setting(
            database.conn,
            KEY_CARRIER_INTERVAL_HOURS,
            str(_clamp_interval(carrier_interval_hours)),
        )
        set_setting(
            database.conn,
            KEY_INITIAL_DELAY_SEC,
            str(max(0.0, initial_delay_sec)),
        )
        database.conn.commit()
    return get_scheduled_sync_settings(database)


def record_internal_batch_finished(database: Database) -> None:
    from ..db.datetime_util import now_str

    with database.lock:
        set_setting(database.conn, KEY_INTERNAL_LAST_FINISHED, now_str())
        database.conn.commit()


def get_last_internal_batch_finished(database: Database) -> str | None:
    with database.lock:
        return get_setting(database.conn, KEY_INTERNAL_LAST_FINISHED)
