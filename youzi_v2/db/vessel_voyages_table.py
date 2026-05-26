"""航次主表 + 挂靠港口表。"""

from __future__ import annotations

import sqlite3

VOYAGES_TABLE = "vessel_voyages"
PORT_CALLS_TABLE = "voyage_port_calls"

_CREATE_VOYAGES = f"""
CREATE TABLE IF NOT EXISTS {VOYAGES_TABLE} (
    id TEXT PRIMARY KEY,
    vessel_voyage TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_CREATE_PORT_CALLS = f"""
CREATE TABLE IF NOT EXISTS {PORT_CALLS_TABLE} (
    id TEXT PRIMARY KEY,
    voyage_id TEXT NOT NULL,
    port_name TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 1,
    eta TEXT,
    ata TEXT,
    etd TEXT,
    atd TEXT,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    FOREIGN KEY (voyage_id) REFERENCES {VOYAGES_TABLE}(id) ON DELETE CASCADE
)
"""

_INDEXES = [
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{VOYAGES_TABLE}_vessel_voyage "
    f"ON {VOYAGES_TABLE}(vessel_voyage)",
    f"CREATE INDEX IF NOT EXISTS idx_{PORT_CALLS_TABLE}_voyage_id "
    f"ON {PORT_CALLS_TABLE}(voyage_id)",
    f"CREATE INDEX IF NOT EXISTS idx_{PORT_CALLS_TABLE}_sequence "
    f"ON {PORT_CALLS_TABLE}(voyage_id, sequence)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_VOYAGES)
    conn.execute(_CREATE_PORT_CALLS)
    for sql in _INDEXES:
        conn.execute(sql)
