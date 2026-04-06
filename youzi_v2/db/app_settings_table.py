"""
应用级键值配置表：无业务数据时写入基础默认项，部署后可直接改库或后续做管理界面。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

TABLE_NAME = "app_settings"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )


def seed_if_empty(conn: sqlite3.Connection) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    row = conn.execute(
        f"SELECT COUNT(*) AS c FROM {TABLE_NAME}",
    ).fetchone()
    if row and row["c"] and row["c"] > 0:
        return
    defaults: list[tuple[str, str]] = [
        ("app.display_name", "youzi_v2"),
        ("quote_history.max_rows", "100"),
    ]
    conn.executemany(
        f"""
        INSERT OR IGNORE INTO {TABLE_NAME} (key, value, updated_at)
        VALUES (?, ?, ?)
        """,
        [(k, v, now) for k, v in defaults],
    )


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute(
        f"SELECT value FROM {TABLE_NAME} WHERE key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return default
    return str(row["value"])


def get_int_setting(conn: sqlite3.Connection, key: str, default: int) -> int:
    raw = get_setting(conn, key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def set_setting(conn: sqlite3.Connection, key: str, value: Any) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        f"""
        INSERT INTO {TABLE_NAME} (key, value, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, str(value), now),
    )
