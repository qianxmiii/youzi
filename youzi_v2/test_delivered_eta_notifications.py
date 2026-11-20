import sqlite3
import threading
import unittest
from types import SimpleNamespace
from .db.shipment_subscriptions_table import ShipmentSubscriptionsRepository, SHIPMENTS_TABLE, NOTIFICATIONS_TABLE

class DeliveredEtaTests(unittest.TestCase):
    def test_only_delivered_eta_notifications_are_read(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(f"CREATE TABLE {SHIPMENTS_TABLE} (id TEXT, status_code TEXT, delivered_time TEXT)")
        conn.execute(f"CREATE TABLE {NOTIFICATIONS_TABLE} (id TEXT, shipment_id TEXT, tracking_source TEXT, read_at TEXT)")
        conn.executemany(f"INSERT INTO {SHIPMENTS_TABLE} VALUES (?, ?, ?)", [("status", " delivered ", ""), ("time", "TRANSIT", "2026-01-01"), ("active", "TRANSIT", " ")])
        conn.executemany(f"INSERT INTO {NOTIFICATIONS_TABLE} VALUES (?, ?, ?, ?)", [("a", "status", "eta_reminder", ""), ("b", "time", "eta_reminder", ""), ("c", "active", "eta_reminder", ""), ("d", "status", "internal", ""), ("e", "status", "carrier", ""), ("f", "status", "eta_reminder", "original")])
        repo = ShipmentSubscriptionsRepository(SimpleNamespace(conn=conn, lock=threading.RLock()))
        self.assertEqual(repo._mark_delivered_eta_reminders_read_locked(), 2)
        rows = {r["id"]: r["read_at"] for r in conn.execute(f"SELECT * FROM {NOTIFICATIONS_TABLE}")}
        self.assertTrue(rows["a"])
        self.assertTrue(rows["b"])
        self.assertEqual([rows[k] for k in ("c", "d", "e")], ["", "", ""])
        self.assertEqual(rows["f"], "original")
        self.assertEqual(repo._mark_delivered_eta_reminders_read_locked(), 0)
        conn.close()
