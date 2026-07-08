from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_instance: "Database | None" = None
_instance_lock = threading.Lock()


class Database:
    """单文件 SQLite，线程内复用连接；启动时挂载各表的 ensure_schema / seed。"""

    def __init__(self, db_path: Path) -> None:
        self._lock = threading.RLock()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = db_path
        self._conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
            timeout=30.0,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=30000")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._bootstrap()

    def _bootstrap(self) -> None:
        from . import addresses_table
        from . import addresses_warehouse_table
        from . import app_settings_table
        from . import code_tables
        from . import dict_table
        from . import quote_history_table
        from . import shipments_table
        from . import shipment_exception_events_table
        from . import shipment_exception_followup_table
        from . import channel_sla_rules_table
        from . import shipment_sla_alert_followups_table
        from . import shipment_sla_alerts_table
        from . import carrier_tracking_logs_table
        from . import internal_tracking_logs_table
        from . import tracking_sync_jobs_table
        from . import customers_table
        from . import shipment_tracking_numbers_table
        from . import port_subscriptions_table
        from . import shipment_subscriptions_table
        from . import shipment_groups_table
        from . import shipment_tracking_time_candidates_table
        from . import vessel_voyages_table

        with self._lock:
            app_settings_table.ensure_schema(self._conn)
            code_tables.ensure_schema(self._conn)
            dict_table.ensure_schema(self._conn)
            quote_history_table.ensure_schema(self._conn)
            addresses_table.ensure_schema(self._conn)
            addresses_warehouse_table.ensure_schema(self._conn)
            shipments_table.ensure_schema(self._conn)
            shipment_exception_events_table.ensure_schema(self._conn)
            shipment_exception_followup_table.ensure_schema(self._conn)
            channel_sla_rules_table.ensure_schema(self._conn)
            shipment_sla_alerts_table.ensure_schema(self._conn)
            shipment_sla_alert_followups_table.ensure_schema(self._conn)
            internal_tracking_logs_table.ensure_schema(self._conn)
            carrier_tracking_logs_table.ensure_schema(self._conn)
            tracking_sync_jobs_table.ensure_schema(self._conn)
            customers_table.ensure_schema(self._conn)
            shipment_tracking_numbers_table.ensure_schema(self._conn)
            vessel_voyages_table.ensure_schema(self._conn)
            port_subscriptions_table.ensure_schema(self._conn)
            shipment_subscriptions_table.ensure_schema(self._conn)
            shipment_groups_table.ensure_schema(self._conn)
            shipment_tracking_time_candidates_table.ensure_schema(self._conn)
            self._conn.commit()
        app_settings_table.seed_if_empty(self._conn)
        code_tables.seed_if_empty(self._conn)
        dict_table.seed_if_empty(self._conn)
        addresses_table.seed_if_empty(self._conn)
        addresses_warehouse_table.seed_if_empty(self._conn)
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    @property
    def path(self) -> Path:
        return self._path


def get_database(db_path: Path) -> Database:
    global _instance
    with _instance_lock:
        if _instance is None or _instance.path != db_path:
            _instance = Database(db_path)
        return _instance
