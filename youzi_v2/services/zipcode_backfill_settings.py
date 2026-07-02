"""运单邮编回写计划任务配置（app_settings）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..db.app_settings_table import get_setting, set_setting
from ..db.connection import Database
from ..db.datetime_util import now_str
from .scheduled_sync_settings import _parse_bool

KEY_ZIPCODE_BACKFILL_ENABLED = "shipments.zipcode_backfill.enabled"
KEY_ZIPCODE_BACKFILL_LAST_FINISHED = "shipments.zipcode_backfill.last_finished_at"

ZIPCODE_BACKFILL_INTERVAL_HOURS = 24.0


@dataclass(frozen=True)
class ZipcodeBackfillSettings:
    enabled: bool
    last_finished: str | None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "zipcodeBackfillEnabled": self.enabled,
            "zipcodeBackfillLastFinished": self.last_finished,
        }


def ensure_zipcode_backfill_defaults(conn) -> None:
    if get_setting(conn, KEY_ZIPCODE_BACKFILL_ENABLED) is None:
        set_setting(conn, KEY_ZIPCODE_BACKFILL_ENABLED, "0")


def get_zipcode_backfill_settings(database: Database) -> ZipcodeBackfillSettings:
    with database.lock:
        ensure_zipcode_backfill_defaults(database.conn)
        enabled = _parse_bool(
            get_setting(database.conn, KEY_ZIPCODE_BACKFILL_ENABLED),
            False,
        )
        last_finished = get_setting(database.conn, KEY_ZIPCODE_BACKFILL_LAST_FINISHED)
    return ZipcodeBackfillSettings(
        enabled=enabled,
        last_finished=last_finished,
    )


def save_zipcode_backfill_enabled(database: Database, *, enabled: bool) -> ZipcodeBackfillSettings:
    with database.lock:
        ensure_zipcode_backfill_defaults(database.conn)
        set_setting(database.conn, KEY_ZIPCODE_BACKFILL_ENABLED, "1" if enabled else "0")
        database.conn.commit()
    return get_zipcode_backfill_settings(database)


def record_zipcode_backfill_finished(database: Database) -> None:
    with database.lock:
        set_setting(database.conn, KEY_ZIPCODE_BACKFILL_LAST_FINISHED, now_str())
        database.conn.commit()
