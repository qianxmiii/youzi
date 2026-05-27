"""航次主表 + 挂靠港口表。"""

from __future__ import annotations

import sqlite3

VOYAGES_TABLE = "vessel_voyages"
PORT_CALLS_TABLE = "voyage_port_calls"

_CREATE_VOYAGES = f"""
CREATE TABLE IF NOT EXISTS {VOYAGES_TABLE} (
    id TEXT PRIMARY KEY,
    vessel_voyage TEXT NOT NULL,
    vessel_name TEXT,
    voyage_no TEXT,
    vessel_code TEXT,
    shipping_company TEXT,
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
    f"CREATE INDEX IF NOT EXISTS idx_{VOYAGES_TABLE}_vessel_code "
    f"ON {VOYAGES_TABLE}(vessel_code)",
    f"CREATE INDEX IF NOT EXISTS idx_{PORT_CALLS_TABLE}_voyage_id "
    f"ON {PORT_CALLS_TABLE}(voyage_id)",
    f"CREATE INDEX IF NOT EXISTS idx_{PORT_CALLS_TABLE}_sequence "
    f"ON {PORT_CALLS_TABLE}(voyage_id, sequence)",
]

_EXTRA_VOYAGE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("vessel_name", "TEXT"),
    ("voyage_no", "TEXT"),
    ("vessel_code", "TEXT"),
    ("shipping_company", "TEXT"),
)


def _backfill_voyage_split(conn: sqlite3.Connection) -> None:
    from youzi_v2.services.vessel_voyage_fields import parse_vessel_voyage

    rows = conn.execute(
        f"""
        SELECT id, vessel_voyage, vessel_name, voyage_no
        FROM {VOYAGES_TABLE}
        WHERE TRIM(COALESCE(vessel_voyage, '')) != ''
        """
    ).fetchall()
    for row in rows:
        if (row["vessel_name"] or "").strip() and (row["voyage_no"] or "").strip():
            continue
        name, voyage = parse_vessel_voyage(row["vessel_voyage"])
        if not name and not voyage:
            continue
        conn.execute(
            f"""
            UPDATE {VOYAGES_TABLE}
            SET vessel_name = COALESCE(NULLIF(TRIM(vessel_name), ''), ?),
                voyage_no = COALESCE(NULLIF(TRIM(voyage_no), ''), ?)
            WHERE id = ?
            """,
            (name, voyage, row["id"]),
        )


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_VOYAGES)
    conn.execute(_CREATE_PORT_CALLS)
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({VOYAGES_TABLE})").fetchall()}
    for col_name, col_type in _EXTRA_VOYAGE_COLUMNS:
        if col_name not in cols:
            conn.execute(f"ALTER TABLE {VOYAGES_TABLE} ADD COLUMN {col_name} {col_type}")
    for sql in _INDEXES:
        conn.execute(sql)
    _backfill_voyage_split(conn)
