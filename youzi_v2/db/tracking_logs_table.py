"""
运单轨迹表 tracking_logs：一个运单号对应多条轨迹，按 tracking_time 排序展示。
"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "tracking_logs"

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
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_shipment_time ON {TABLE_NAME}(shipment_no, tracking_time DESC)",
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_dedup "
    f"ON {TABLE_NAME}(shipment_no, tracking_time, tracking_desc)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE_NAME,),
    )
    if cur.fetchone() is None:
        conn.execute(_CREATE_SQL)
        for stmt in _INDEXES:
            conn.execute(stmt)
        return

    _dedupe_and_ensure_unique(conn)


def _dedupe_and_ensure_unique(conn: sqlite3.Connection) -> None:
    """去重后创建唯一索引，支持增量 INSERT OR IGNORE。"""
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
