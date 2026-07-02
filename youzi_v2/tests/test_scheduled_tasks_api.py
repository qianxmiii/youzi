"""计划任务 API 数据层。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from youzi_v2.services.scheduled_sync_settings import (
    get_scheduled_sync_settings,
    save_scheduled_sync_settings,
)
from youzi_v2.services.scheduled_tasks_info import (
    build_scheduled_task_config,
    builtin_scheduled_tasks,
)


class ScheduledTasksInfoTest(unittest.TestCase):
    def test_builtin_tasks_include_zipcode_backfill(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        settings = get_scheduled_sync_settings(db)
        tasks = builtin_scheduled_tasks(settings, db)
        self.assertGreaterEqual(len(tasks), 3)
        sources = {t["source"] for t in tasks}
        self.assertIn("zipcode-backfill", sources)
        self.assertIn("dps-shipment-sync", sources)
        db.conn.close()
        tmp.cleanup()

    def test_builtin_tasks_tracking_entries(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        settings = get_scheduled_sync_settings(db)
        tasks = builtin_scheduled_tasks(settings, db)
        tracking = [t for t in tasks if t["source"] in ("internal", "carrier")]
        self.assertEqual(len(tracking), 2)
        sources = {t["source"] for t in tracking}
        self.assertEqual(sources, {"internal", "carrier"})
        db.conn.close()
        tmp.cleanup()

    def test_list_jobs_pagination(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        repo = TrackingSyncJobsRepository(db)
        jid = repo.create_job("carrier", "scheduled")
        repo.finish_job(
            jid,
            status="success",
            total_shipments=10,
            updated_shipments=3,
            new_log_count=5,
        )
        data = repo.list_jobs(limit=10, offset=0)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["triggerType"], "scheduled")
        db.conn.close()
        tmp.cleanup()

    def test_save_and_read_settings(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        saved = save_scheduled_sync_settings(
            db,
            internal_enabled=True,
            internal_interval_hours=3,
            carrier_enabled=False,
            carrier_interval_hours=2,
            initial_delay_sec=30,
        )
        self.assertTrue(saved.internal_enabled)
        self.assertEqual(saved.internal_interval_hours, 3.0)
        self.assertFalse(saved.carrier_enabled)
        cfg = build_scheduled_task_config(db)
        self.assertTrue(cfg["internalEnabled"])
        self.assertFalse(cfg["carrierEnabled"])
        db.conn.close()
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
