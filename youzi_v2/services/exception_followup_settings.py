"""异常跟进提醒计划任务配置（app_settings）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..db.app_settings_table import get_setting, set_setting
from ..db.connection import Database
from ..db.datetime_util import now_str
from .scheduled_sync_settings import _parse_bool

KEY_EXCEPTION_FOLLOWUP_ENABLED = "exceptions.followup.enabled"
KEY_EXCEPTION_FOLLOWUP_LAST_FINISHED = "exceptions.followup.last_finished_at"

EXCEPTION_FOLLOWUP_INTERVAL_HOURS = 24.0


@dataclass(frozen=True)
class ExceptionFollowupSettings:
    enabled: bool
    last_finished: str | None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "exceptionFollowupEnabled": self.enabled,
            "exceptionFollowupLastFinished": self.last_finished,
        }


def ensure_exception_followup_defaults(conn) -> None:
    if get_setting(conn, KEY_EXCEPTION_FOLLOWUP_ENABLED) is None:
        set_setting(conn, KEY_EXCEPTION_FOLLOWUP_ENABLED, "0")


def get_exception_followup_settings(database: Database) -> ExceptionFollowupSettings:
    with database.lock:
        ensure_exception_followup_defaults(database.conn)
        enabled = _parse_bool(
            get_setting(database.conn, KEY_EXCEPTION_FOLLOWUP_ENABLED),
            False,
        )
        last_finished = get_setting(database.conn, KEY_EXCEPTION_FOLLOWUP_LAST_FINISHED)
    return ExceptionFollowupSettings(
        enabled=enabled,
        last_finished=last_finished,
    )


def save_exception_followup_enabled(
    database: Database,
    *,
    enabled: bool,
) -> ExceptionFollowupSettings:
    with database.lock:
        ensure_exception_followup_defaults(database.conn)
        set_setting(database.conn, KEY_EXCEPTION_FOLLOWUP_ENABLED, "1" if enabled else "0")
        database.conn.commit()
    return get_exception_followup_settings(database)


def record_exception_followup_scan_finished(database: Database) -> None:
    with database.lock:
        set_setting(database.conn, KEY_EXCEPTION_FOLLOWUP_LAST_FINISHED, now_str())
        database.conn.commit()
