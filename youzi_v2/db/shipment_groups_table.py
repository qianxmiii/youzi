"""运单分组：shipment_groups + shipment_group_members。"""

from __future__ import annotations

import sqlite3

GROUPS_TABLE = "shipment_groups"
MEMBERS_TABLE = "shipment_group_members"
TYPES_TABLE = "shipment_group_types"
RULES_TABLE = "shipment_group_rules"
NOTIFICATIONS_TABLE = "shipment_group_notifications"

_CREATE_GROUPS_SQL = f"""
CREATE TABLE IF NOT EXISTS {GROUPS_TABLE} (
    id TEXT PRIMARY KEY,
    group_no TEXT NOT NULL UNIQUE,
    group_name TEXT NOT NULL DEFAULT '',
    primary_type TEXT NOT NULL DEFAULT 'MANUAL',
    customer TEXT,
    customer_no TEXT,
    vessel_voyage TEXT,
    destination_port_code TEXT,
    payment_status TEXT NOT NULL DEFAULT 'UNPAID',
    payment_due_rule TEXT NOT NULL DEFAULT 'LAST_ARRIVAL',
    note TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
"""

_CREATE_TYPES_SQL = f"""
CREATE TABLE IF NOT EXISTS {TYPES_TABLE} (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    group_type TEXT NOT NULL,
    created_time TEXT NOT NULL,
    UNIQUE(group_id, group_type)
)
"""

_CREATE_MEMBERS_SQL = f"""
CREATE TABLE IF NOT EXISTS {MEMBERS_TABLE} (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'NORMAL',
    batch_no TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    UNIQUE(group_id, shipment_id)
)
"""

_CREATE_RULES_SQL = f"""
CREATE TABLE IF NOT EXISTS {RULES_TABLE} (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    threshold_days INTEGER,
    warning_days INTEGER,
    trigger_status TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{{}}',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    UNIQUE(group_id, rule_type)
)
"""

_CREATE_NOTIFICATIONS_SQL = f"""
CREATE TABLE IF NOT EXISTS {NOTIFICATIONS_TABLE} (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning',
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    shipment_no TEXT NOT NULL DEFAULT '',
    event_key TEXT NOT NULL UNIQUE,
    triggered_at TEXT NOT NULL,
    read_at TEXT NOT NULL DEFAULT '',
    resolved_at TEXT NOT NULL DEFAULT ''
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{GROUPS_TABLE}_customer "
    f"ON {GROUPS_TABLE}(customer)",
    f"CREATE INDEX IF NOT EXISTS idx_{GROUPS_TABLE}_vessel_voyage "
    f"ON {GROUPS_TABLE}(vessel_voyage)",
    f"CREATE INDEX IF NOT EXISTS idx_{TYPES_TABLE}_group_id "
    f"ON {TYPES_TABLE}(group_id)",
    f"CREATE INDEX IF NOT EXISTS idx_{TYPES_TABLE}_group_type "
    f"ON {TYPES_TABLE}(group_type)",
    f"CREATE INDEX IF NOT EXISTS idx_{MEMBERS_TABLE}_group_id "
    f"ON {MEMBERS_TABLE}(group_id)",
    f"CREATE INDEX IF NOT EXISTS idx_{MEMBERS_TABLE}_shipment_id "
    f"ON {MEMBERS_TABLE}(shipment_id)",
    f"CREATE INDEX IF NOT EXISTS idx_{MEMBERS_TABLE}_shipment_no "
    f"ON {MEMBERS_TABLE}(shipment_no)",
    f"CREATE INDEX IF NOT EXISTS idx_{RULES_TABLE}_group_id "
    f"ON {RULES_TABLE}(group_id)",
    f"CREATE INDEX IF NOT EXISTS idx_{NOTIFICATIONS_TABLE}_group_unread "
    f"ON {NOTIFICATIONS_TABLE}(group_id, read_at, triggered_at)",
    f"CREATE INDEX IF NOT EXISTS idx_{NOTIFICATIONS_TABLE}_event_key "
    f"ON {NOTIFICATIONS_TABLE}(event_key)",
]


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r[1]) for r in rows}


def _migrate_groups_primary_type(conn: sqlite3.Connection) -> None:
    cols = _table_columns(conn, GROUPS_TABLE)
    if "primary_type" not in cols and "group_type" in cols:
        conn.execute(
            f"ALTER TABLE {GROUPS_TABLE} RENAME COLUMN group_type TO primary_type"
        )
    elif "primary_type" not in cols:
        conn.execute(
            f"ALTER TABLE {GROUPS_TABLE} ADD COLUMN primary_type TEXT NOT NULL DEFAULT 'MANUAL'"
        )


def _migrate_rule_type_names(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        UPDATE {RULES_TABLE}
        SET rule_type = 'GROUP_ARRIVED_PAYMENT'
        WHERE rule_type = 'LAST_BATCH_ARRIVED_PAYMENT'
        """
    )
    conn.execute(
        f"""
        UPDATE {NOTIFICATIONS_TABLE}
        SET rule_type = 'GROUP_ARRIVED_PAYMENT'
        WHERE rule_type = 'LAST_BATCH_ARRIVED_PAYMENT'
        """
    )


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_GROUPS_SQL)
    _migrate_groups_primary_type(conn)
    conn.execute(_CREATE_MEMBERS_SQL)
    conn.execute(_CREATE_TYPES_SQL)
    conn.execute(_CREATE_RULES_SQL)
    conn.execute(_CREATE_NOTIFICATIONS_SQL)
    _migrate_rule_type_names(conn)
    for sql in _INDEXES:
        conn.execute(sql)
