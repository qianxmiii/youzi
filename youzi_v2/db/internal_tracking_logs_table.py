"""
内部路由轨迹表 internal_tracking_logs（原 tracking_logs）。
"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "internal_tracking_logs"

# 异常跟踪按轨迹记录时间判断停更，包含通用摘要过滤的入库文案。
# 使用 shipment_no / tracking_time 索引逐票定位最新一条。
LATEST_INTERNAL_LOG_JOIN = f"""
    LEFT JOIN {TABLE_NAME} latest_internal ON latest_internal.rowid = (
        SELECT log.rowid
        FROM {TABLE_NAME} log
        WHERE log.shipment_no = s.shipment_no AND log.tracking_time <> ''
        ORDER BY log.tracking_time DESC, log.rowid DESC
        LIMIT 1
    )
"""
LATEST_INTERNAL_LOG_TIME = "COALESCE(latest_internal.tracking_time, s.latest_tracking_time)"
LATEST_INTERNAL_LOG_DESC = "COALESCE(latest_internal.tracking_desc, s.latest_tracking_desc)"
LEGACY_TABLE = "tracking_logs"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    shipment_no TEXT NOT NULL,
    tracking_time TEXT NOT NULL,
    tracking_desc TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_no ON {TABLE_NAME}(shipment_no)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_time "
    f"ON {TABLE_NAME}(shipment_no, tracking_time DESC)",
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_dedup "
    f"ON {TABLE_NAME}(shipment_no, tracking_time, tracking_desc)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    legacy = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (LEGACY_TABLE,),
    ).fetchone()
    current = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE_NAME,),
    ).fetchone()
    if current is None and legacy is not None:
        conn.execute(f"ALTER TABLE {LEGACY_TABLE} RENAME TO {TABLE_NAME}")
    elif current is None:
        conn.execute(_CREATE_SQL)
    for stmt in _INDEXES:
        conn.execute(stmt)
    _dedupe_and_ensure_unique(conn)


def _dedupe_and_ensure_unique(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        DELETE FROM {TABLE_NAME}
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM {TABLE_NAME}
            GROUP BY shipment_no, tracking_time, tracking_desc
        )
        """
    )
    conn.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_dedup "
        f"ON {TABLE_NAME}(shipment_no, tracking_time, tracking_desc)"
    )
