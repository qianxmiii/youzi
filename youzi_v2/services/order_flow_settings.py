"""订单流转轮询开关。默认关闭，间隔固定 5 分钟。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..db.app_settings_table import get_setting, set_setting
from ..db.connection import Database
from ..db.datetime_util import now_str
from .scheduled_sync_settings import _parse_bool

KEY_ENABLED = "order_flow.poll.enabled"
KEY_LAST_FINISHED = "order_flow.poll.last_finished_at"
KEY_REMINDER_SEEN = "order_flow.reminder_seen_at"
KEY_LIST_SEEN = "order_flow.list_seen_at"
INTERVAL_SEC = 300


@dataclass(frozen=True)
class OrderFlowPollSettings:
    enabled: bool
    last_finished: str | None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "orderFlowPollEnabled": self.enabled,
            "orderFlowPollLastFinished": self.last_finished,
            "orderFlowPollIntervalSec": INTERVAL_SEC,
        }


def ensure_order_flow_poll_defaults(conn) -> None:
    if get_setting(conn, KEY_ENABLED) is None:
        set_setting(conn, KEY_ENABLED, "0")


def get_order_flow_poll_settings(database: Database) -> OrderFlowPollSettings:
    with database.lock:
        ensure_order_flow_poll_defaults(database.conn)
        enabled = _parse_bool(get_setting(database.conn, KEY_ENABLED), False)
        last_finished = get_setting(database.conn, KEY_LAST_FINISHED)
    return OrderFlowPollSettings(enabled=enabled, last_finished=last_finished)


def save_order_flow_poll_enabled(database: Database, *, enabled: bool) -> OrderFlowPollSettings:
    with database.lock:
        ensure_order_flow_poll_defaults(database.conn)
        set_setting(database.conn, KEY_ENABLED, "1" if enabled else "0")
        database.conn.commit()
    return get_order_flow_poll_settings(database)


def get_order_flow_reminder_seen_at(database: Database) -> str:
    with database.lock:
        return get_setting(database.conn, KEY_REMINDER_SEEN) or ""


def mark_order_flow_reminders_seen(database: Database) -> str:
    seen_at = now_str()
    with database.lock:
        set_setting(database.conn, KEY_REMINDER_SEEN, seen_at)
        database.conn.commit()
    return seen_at


def get_order_flow_list_seen_at(database: Database) -> str:
    with database.lock:
        return get_setting(database.conn, KEY_LIST_SEEN) or ""


def mark_order_flow_list_seen(database: Database) -> str:
    seen_at = now_str()
    with database.lock:
        set_setting(database.conn, KEY_LIST_SEEN, seen_at)
        database.conn.commit()
    return seen_at


def record_order_flow_poll_finished(database: Database) -> None:
    with database.lock:
        set_setting(database.conn, KEY_LAST_FINISHED, now_str())
        database.conn.commit()
