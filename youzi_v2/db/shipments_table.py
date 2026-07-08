"""
运单主表 shipments。
时间列统一 TEXT，格式 YYYY-MM-DD HH:mm:ss。
外键码表为逻辑关联（SQLite 不强制 FK，便于分步导入历史数据）。
"""

from __future__ import annotations

import sqlite3

TABLE_NAME = "shipments"

_CREATE_SQL = f"""
CREATE TABLE {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    shipment_no TEXT NOT NULL UNIQUE,
    customer TEXT,
    customer_no TEXT,
    channel_code TEXT,
    country_code TEXT,
    address_type TEXT CHECK (
        address_type IS NULL OR address_type IN ('AMZ', 'WFS', '3PL')
    ),
    address_code TEXT,
    delivery_address TEXT,
    ctns INTEGER,
    zipcode TEXT,
    product_name TEXT,
    origin_warehouse_code TEXT,
    supplier_name TEXT,
    carrier_code TEXT,
    carrier_id TEXT,
    waybill_id TEXT,
    tracking_number TEXT,
    express_code TEXT,
    customer_shipment_id TEXT,
    amazon_ref_id TEXT,
    vessel_name TEXT,
    voyage_no TEXT,
    vessel_voyage TEXT,
    etd TEXT,
    eta TEXT,
    atd TEXT,
    ata TEXT,
    origin_port_code TEXT,
    destination_port_code TEXT,
    expected_delivery_time TEXT,
    warehouse_entry_time TEXT,
    delivered_time TEXT,
    status_code TEXT,
    exception_code TEXT,
    exception_opened_time TEXT,
    latest_tracking_time TEXT,
    latest_tracking_desc TEXT,
    tracking_log_count INTEGER NOT NULL DEFAULT 0,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_customer ON {TABLE_NAME}(customer)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_channel_code ON {TABLE_NAME}(channel_code)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_country_code ON {TABLE_NAME}(country_code)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_address_type ON {TABLE_NAME}(address_type)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_carrier_code ON {TABLE_NAME}(carrier_code)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_status_code ON {TABLE_NAME}(status_code)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_exception_code ON {TABLE_NAME}(exception_code)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_updated_time ON {TABLE_NAME}(updated_time DESC)",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_latest_tracking_time ON {TABLE_NAME}(latest_tracking_time)",
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

    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
    if "address_type" not in cols:
        conn.execute(
            f"""
            ALTER TABLE {TABLE_NAME}
            ADD COLUMN address_type TEXT CHECK (
                address_type IS NULL OR address_type IN ('AMZ', 'WFS', '3PL')
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_address_type ON {TABLE_NAME}(address_type)"
        )
    if "delivery_address" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN delivery_address TEXT")
    if "ctns" not in cols:
        if "piece_count" in cols:
            conn.execute(f"ALTER TABLE {TABLE_NAME} RENAME COLUMN piece_count TO ctns")
        else:
            conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN ctns INTEGER")
    if "latest_tracking_time" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN latest_tracking_time TEXT")
    if "latest_tracking_desc" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN latest_tracking_desc TEXT")
    if "tracking_log_count" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN tracking_log_count INTEGER NOT NULL DEFAULT 0"
        )
    if "latest_carrier_time" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN latest_carrier_time TEXT")
    if "latest_carrier_desc" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN latest_carrier_desc TEXT")
    if "carrier_log_count" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN carrier_log_count INTEGER NOT NULL DEFAULT 0"
        )
    if "carrier_id" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN carrier_id TEXT")
    if "waybill_id" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN waybill_id TEXT")
    if "tracking_number" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN tracking_number TEXT")
    if "express_code" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN express_code TEXT")
    if "exception_code" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN exception_code TEXT")
    if "exception_opened_time" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN exception_opened_time TEXT")
    if "expected_delivery_time" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN expected_delivery_time TEXT")
    if "warehouse_entry_time" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN warehouse_entry_time TEXT")
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_exception_code "
        f"ON {TABLE_NAME}(exception_code)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_latest_tracking_time "
        f"ON {TABLE_NAME}(latest_tracking_time)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_latest_carrier_time "
        f"ON {TABLE_NAME}(latest_carrier_time)"
    )
    _backfill_tracking_summary(conn)


def _backfill_tracking_summary(conn: sqlite3.Connection) -> None:
    """从 internal_tracking_logs 回填内部轨迹摘要（仅补空摘要的行）。"""
    has_internal = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='internal_tracking_logs'"
    ).fetchone()
    if not has_internal:
        return
    conn.execute(
        f"""
        UPDATE {TABLE_NAME}
        SET latest_tracking_time = (
            SELECT t.tracking_time
            FROM internal_tracking_logs t
            WHERE t.shipment_no = {TABLE_NAME}.shipment_no
            ORDER BY datetime(t.tracking_time) DESC, datetime(t.created_time) DESC
            LIMIT 1
        ),
        latest_tracking_desc = (
            SELECT t.tracking_desc
            FROM internal_tracking_logs t
            WHERE t.shipment_no = {TABLE_NAME}.shipment_no
            ORDER BY datetime(t.tracking_time) DESC, datetime(t.created_time) DESC
            LIMIT 1
        ),
        tracking_log_count = (
            SELECT COUNT(*) FROM internal_tracking_logs t
            WHERE t.shipment_no = {TABLE_NAME}.shipment_no
        )
        WHERE EXISTS (
            SELECT 1 FROM internal_tracking_logs t
            WHERE t.shipment_no = {TABLE_NAME}.shipment_no
        )
        AND (
            latest_tracking_time IS NULL OR latest_tracking_time = ''
            OR tracking_log_count IS NULL OR tracking_log_count = 0
        )
        """
    )
