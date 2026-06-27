"""分组自动归档计划任务配置（app_settings）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..db.app_settings_table import get_setting, set_setting
from ..db.connection import Database
from ..db.datetime_util import now_str
from .scheduled_sync_settings import _parse_bool

KEY_GROUP_AUTO_ARCHIVE_ENABLED = "groups.auto_archive.enabled"
KEY_GROUP_AUTO_ARCHIVE_LAST_FINISHED = "groups.auto_archive.last_finished_at"

GROUP_AUTO_ARCHIVE_INTERVAL_HOURS = 24.0


@dataclass(frozen=True)
class GroupArchiveSettings:
    auto_archive_enabled: bool
    last_finished: str | None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "groupAutoArchiveEnabled": self.auto_archive_enabled,
            "groupAutoArchiveLastFinished": self.last_finished,
        }


def ensure_group_archive_defaults(conn) -> None:
    if get_setting(conn, KEY_GROUP_AUTO_ARCHIVE_ENABLED) is None:
        set_setting(conn, KEY_GROUP_AUTO_ARCHIVE_ENABLED, "0")


def get_group_archive_settings(database: Database) -> GroupArchiveSettings:
    with database.lock:
        ensure_group_archive_defaults(database.conn)
        enabled = _parse_bool(
            get_setting(database.conn, KEY_GROUP_AUTO_ARCHIVE_ENABLED),
            False,
        )
        last_finished = get_setting(database.conn, KEY_GROUP_AUTO_ARCHIVE_LAST_FINISHED)
    return GroupArchiveSettings(
        auto_archive_enabled=enabled,
        last_finished=last_finished,
    )


def save_group_auto_archive_enabled(database: Database, *, enabled: bool) -> GroupArchiveSettings:
    with database.lock:
        ensure_group_archive_defaults(database.conn)
        set_setting(database.conn, KEY_GROUP_AUTO_ARCHIVE_ENABLED, "1" if enabled else "0")
        database.conn.commit()
    return get_group_archive_settings(database)


def record_group_auto_archive_finished(database: Database) -> None:
    with database.lock:
        set_setting(database.conn, KEY_GROUP_AUTO_ARCHIVE_LAST_FINISHED, now_str())
        database.conn.commit()
