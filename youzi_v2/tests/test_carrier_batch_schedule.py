"""承运商全库批处理间隔。"""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from youzi_v2.db import app_settings_table
from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.services.carrier_batch_schedule import (
    SETTING_LAST_CARRIER_BATCH_FINISHED,
    is_carrier_full_batch,
    record_carrier_batch_finished,
    should_run_scheduled_carrier_batch,
)
from youzi_v2.services.scheduled_sync_settings import (
    KEY_CARRIER_ENABLED,
    KEY_CARRIER_INTERVAL_HOURS,
    ensure_scheduled_sync_defaults,
)


class CarrierBatchScheduleTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = Database(Path(self._tmp.name) / "test.db")
        with self.db.lock:
            ensure_scheduled_sync_defaults(self.db.conn)
            app_settings_table.set_setting(self.db.conn, KEY_CARRIER_ENABLED, "1")
            app_settings_table.set_setting(self.db.conn, KEY_CARRIER_INTERVAL_HOURS, "2")
            self.db.conn.commit()

    def tearDown(self) -> None:
        self.db.conn.close()
        self._tmp.cleanup()

    def test_is_carrier_full_batch(self) -> None:
        self.assertTrue(is_carrier_full_batch(None))
        self.assertTrue(is_carrier_full_batch([]))
        self.assertFalse(is_carrier_full_batch(["A001"]))

    def test_skip_when_disabled(self) -> None:
        with self.db.lock:
            app_settings_table.set_setting(self.db.conn, KEY_CARRIER_ENABLED, "0")
            self.db.conn.commit()
        ok, reason = should_run_scheduled_carrier_batch(self.db)
        self.assertFalse(ok)
        self.assertIn("关闭", reason or "")

    def test_skip_when_within_interval(self) -> None:
        recent = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        with self.db.lock:
            app_settings_table.set_setting(
                self.db.conn,
                SETTING_LAST_CARRIER_BATCH_FINISHED,
                recent,
            )
            self.db.conn.commit()
        ok, reason = should_run_scheduled_carrier_batch(self.db)
        self.assertFalse(ok)
        self.assertIn("未满", reason or "")

    def test_run_when_interval_elapsed(self) -> None:
        old = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        with self.db.lock:
            app_settings_table.set_setting(
                self.db.conn,
                SETTING_LAST_CARRIER_BATCH_FINISHED,
                old,
            )
            self.db.conn.commit()
        ok, _ = should_run_scheduled_carrier_batch(self.db)
        self.assertTrue(ok)

    def test_record_finished(self) -> None:
        record_carrier_batch_finished(self.db)
        raw = app_settings_table.get_setting(
            self.db.conn,
            SETTING_LAST_CARRIER_BATCH_FINISHED,
        )
        self.assertTrue(raw)
        self.assertEqual(len(now_str()), len(raw or ""))


if __name__ == "__main__":
    unittest.main()
