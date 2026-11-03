"""Independent per-shipment delivery windows; never updates SLA deadlines."""

import sqlite3


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipment_delivery_windows (
            shipment_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL DEFAULT 'auto',
            manual_start TEXT,
            manual_end TEXT,
            updated_time TEXT NOT NULL
        )
    """)


def load_window(conn: sqlite3.Connection, shipment_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM shipment_delivery_windows WHERE shipment_id = ?", (shipment_id,)
    ).fetchone()
    return dict(row) if row else {}


def save_window(conn: sqlite3.Connection, shipment_id: str, values: dict) -> None:
    conn.execute("""
        INSERT INTO shipment_delivery_windows (shipment_id, mode, manual_start, manual_end, updated_time)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(shipment_id) DO UPDATE SET mode=excluded.mode,
            manual_start=excluded.manual_start, manual_end=excluded.manual_end,
            updated_time=excluded.updated_time
    """, (shipment_id, values['mode'], values['manual_start'], values['manual_end'], values['updated_time']))

