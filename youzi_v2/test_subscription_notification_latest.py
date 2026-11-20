"""订阅铃铛按运单保留最新消息。"""

import sqlite3
import threading
import unittest
from types import SimpleNamespace

from .db.shipment_subscriptions_table import (
    NOTIFICATIONS_TABLE,
    ShipmentSubscriptionsRepository,
    ensure_schema,
)


class LatestNotificationTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        self.conn.execute('CREATE TABLE shipments (id TEXT, customer TEXT, status_code TEXT, delivered_time TEXT)')
        ensure_schema(self.conn)
        self.repo = ShipmentSubscriptionsRepository(SimpleNamespace(conn=self.conn, lock=threading.RLock()))

    def add(self, shipment, source, time='2026-01-01 12:00:00'):
        return self.repo._create_tracking_notification_locked(
            subscription_id=shipment, shipment_id=shipment, shipment_no=shipment,
            vessel_voyage='', destination_port_code='', source=source,
            latest_time=time, latest_desc='test',
        )['id']

    def test_same_second_cross_source_and_limit(self):
        self.add('example-a', 'internal')
        newest = self.add('example-a', 'carrier')
        self.add('example-b', 'eta_reminder')
        self.assertEqual(self.repo.count_unread_notifications(), 2)
        self.assertEqual(len(self.repo.list_unread_notifications(limit=1)), 1)
        self.assertEqual({n['id'] for n in self.repo.list_unread_notifications()},
                         {newest, self.conn.execute(f'SELECT id FROM {NOTIFICATIONS_TABLE} ORDER BY rowid DESC LIMIT 1').fetchone()[0]})
        self.repo.mark_notification_read(newest)
        self.assertEqual(self.repo.count_unread_notifications(), 1)
        self.assertEqual(len(self.repo.list_unread_notifications()), 1)
        self.add('example-a', 'internal')
        self.assertEqual(self.repo.count_unread_notifications(), 2)

    def test_latest_read_does_not_reveal_older_unread(self):
        self.add('example-a', 'internal')
        latest = self.add('example-a', 'carrier')
        self.repo.mark_notification_read(latest)
        self.assertEqual(self.repo.list_unread_notifications(), [])
        self.assertEqual(self.repo.count_unread_notifications(), 0)

    def test_creation_time_precedes_insertion_order(self):
        latest = self.add('example-a', 'internal')
        older = self.add('example-a', 'carrier')
        self.conn.execute(f'UPDATE {NOTIFICATIONS_TABLE} SET created_at = ? WHERE id = ?',
                          ('2000-01-01 00:00:00', older))
        self.assertEqual([n['id'] for n in self.repo.list_unread_notifications()], [latest])


if __name__ == '__main__':
    unittest.main()
