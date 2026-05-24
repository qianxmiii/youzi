"""承运商轨迹条目指纹与比对。"""

from __future__ import annotations

import unittest

from youzi_v2.carrier_tracking_entry import (
    CarrierTrackingLogEntry,
    carrier_logs_unchanged,
)


class CarrierTrackingEntryTest(unittest.TestCase):
    def test_same_event_id_different_desc_not_unchanged(self) -> None:
        old = [CarrierTrackingLogEntry.from_row("2026-05-22 09:56:26", "到港", "topda:1")]
        new = [CarrierTrackingLogEntry.from_row("2026-05-22 09:56:26", "已改", "topda:1")]
        self.assertFalse(carrier_logs_unchanged(old, new))

    def test_same_event_id_same_content_unchanged(self) -> None:
        rows = [CarrierTrackingLogEntry.from_row("2026-05-22 09:56:26", "到港", "topda:1")]
        self.assertTrue(carrier_logs_unchanged(rows, list(rows)))


if __name__ == "__main__":
    unittest.main()
