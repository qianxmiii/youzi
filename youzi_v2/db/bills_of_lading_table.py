"""提单航次绑定及运单的最新清关节点。"""

import sqlite3


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bill_of_lading_bindings (
            bill_no TEXT PRIMARY KEY,
            voyage_id TEXT NOT NULL,
            origin_call_id TEXT NOT NULL,
            destination_call_id TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipment_customs_nodes (
            shipment_no TEXT NOT NULL,
            phase TEXT NOT NULL,
            status TEXT NOT NULL,
            node_time TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (shipment_no, phase)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_shipments_bill_no_normalized
        ON shipments (UPPER(TRIM(bill_of_lading_no)))
        WHERE TRIM(COALESCE(bill_of_lading_no, '')) <> ''
    """)
