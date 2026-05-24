"""承运商轨迹按票对齐（reconcile）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from youzi_v2.carrier_tracking_entry import CarrierTrackingLogEntry
from youzi_v2.db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from youzi_v2.db.connection import Database


class CarrierTrackingReconcileTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._db = Database(Path(self._tmp.name) / "test.db")
        self.repo = CarrierTrackingLogsRepository(self._db)
        self.sn = "DPSECO260417030"
        self.vendor = "拓普达供应商"

    def tearDown(self) -> None:
        self._db.conn.close()
        self._tmp.cleanup()

    def test_reconcile_inserts_new(self) -> None:
        r = self.repo.reconcile_logs_for_shipment(
            self.sn,
            self.vendor,
            "TOPDA",
            [("2026-05-22 09:56:26", "到港")],
        )
        self.assertFalse(r["unchanged"])
        self.assertEqual(r["inserted"], 1)
        self.assertEqual(self.repo.count_by_shipment_no(self.sn), 1)

    def test_reconcile_unchanged_when_same(self) -> None:
        logs = [
            ("2026-05-22 09:56:40", "已卸船"),
            ("2026-05-22 09:56:26", "到港"),
        ]
        self.repo.reconcile_logs_for_shipment(self.sn, self.vendor, "TOPDA", logs)
        r2 = self.repo.reconcile_logs_for_shipment(self.sn, self.vendor, "TOPDA", logs)
        self.assertTrue(r2["unchanged"])
        self.assertEqual(r2["inserted"], 0)
        self.assertEqual(r2["deleted"], 0)
        self.assertEqual(self.repo.count_by_shipment_no(self.sn), 2)

    def test_reconcile_removes_stale_and_replaces(self) -> None:
        self.repo.reconcile_logs_for_shipment(
            self.sn,
            self.vendor,
            "TOPDA",
            [
                ("2026-05-22 09:56:26", "错误节点"),
                ("2026-05-21 10:00:00", "旧节点"),
            ],
        )
        api = [
            CarrierTrackingLogEntry.from_row("2026-05-22 09:56:26", "到港", "topda:26917259"),
            CarrierTrackingLogEntry.from_row("2026-05-22 09:56:40", "已卸船", "topda:26917295"),
        ]
        r = self.repo.reconcile_logs_for_shipment(self.sn, self.vendor, "TOPDA", api)
        self.assertFalse(r["unchanged"])
        self.assertEqual(r["inserted"], 2)
        self.assertGreaterEqual(r["deleted"], 1)
        entries = self.repo._list_entries_for_vendor(self.sn, self.vendor)
        keys = {e.match_key() for e in entries}
        self.assertIn("id:topda:26917259", keys)
        self.assertIn("id:topda:26917295", keys)

    def test_reconcile_updates_desc_when_same_event_id(self) -> None:
        eid = "topda:26917259"
        self.repo.reconcile_logs_for_shipment(
            self.sn,
            self.vendor,
            "TOPDA",
            [CarrierTrackingLogEntry.from_row("2026-05-22 09:56:26", "旧文案", eid)],
        )
        r = self.repo.reconcile_logs_for_shipment(
            self.sn,
            self.vendor,
            "TOPDA",
            [CarrierTrackingLogEntry.from_row("2026-05-22 09:56:26", "新文案", eid)],
        )
        self.assertFalse(r["unchanged"])
        rows = self.repo._list_entries_for_vendor(self.sn, self.vendor)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].vendor_event_id, eid)
        self.assertEqual(rows[0].tracking_desc, "新文案")

    def test_reconcile_same_time_desc_different_event_id(self) -> None:
        """TX等同时间同文案、不同 billTrackNo 应能并存。"""
        desc = "报关放行：国内报关已放行，等待出发"
        api = [
            CarrierTrackingLogEntry.from_row(
                "2026-04-27 16:11:35", desc, "txfba:2049067670449319942"
            ),
            CarrierTrackingLogEntry.from_row(
                "2026-04-27 16:11:35", desc, "txfba:2049067668477997063"
            ),
        ]
        r = self.repo.reconcile_logs_for_shipment(self.sn, "腾信", "TX", api)
        self.assertFalse(r["unchanged"])
        self.assertEqual(r["inserted"], 2)
        entries = self.repo._list_entries_for_vendor(self.sn, "腾信")
        self.assertEqual(len(entries), 2)

    def test_reconcile_empty_api_clears_vendor_logs(self) -> None:
        self.repo.reconcile_logs_for_shipment(
            self.sn, self.vendor, "TOPDA", [("2026-05-01 12:00:00", "测试")]
        )
        r = self.repo.reconcile_logs_for_shipment(self.sn, self.vendor, "TOPDA", [])
        self.assertFalse(r["unchanged"])
        self.assertEqual(r["inserted"], 0)
        self.assertGreater(r["deleted"], 0)
        self.assertEqual(len(self.repo._list_entries_for_vendor(self.sn, self.vendor)), 0)


if __name__ == "__main__":
    unittest.main()
