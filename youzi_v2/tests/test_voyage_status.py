"""航次状态计算单元测试。"""

from __future__ import annotations

import unittest
from datetime import datetime

from youzi_v2.services.voyage_status import port_call_status, shipment_maritime_status


class VoyageStatusTests(unittest.TestCase):
    def test_port_call_departed_when_atd_set(self):
        self.assertEqual(
            port_call_status(eta=None, ata=None, etd=None, atd="2026-05-11 12:00:00"),
            "departed",
        )

    def test_port_call_arrived_when_ata_without_atd(self):
        self.assertEqual(
            port_call_status(
                eta=None,
                ata="2026-05-12 11:30:00",
                etd="2026-05-13 06:00:00",
                atd=None,
            ),
            "arrived",
        )

    def test_shipment_arriving_soon(self):
        now = datetime(2026, 5, 26, 12, 0, 0)
        self.assertEqual(
            shipment_maritime_status(
                eta="2026-05-28 16:30:00",
                ata=None,
                etd=None,
                atd=None,
                now=now,
            ),
            "arriving_soon",
        )

    def test_shipment_in_transit(self):
        self.assertEqual(
            shipment_maritime_status(
                eta="2026-06-04 00:00:00",
                ata=None,
                etd="2026-05-21 00:00:00",
                atd="2026-05-21 08:00:00",
            ),
            "in_transit",
        )


if __name__ == "__main__":
    unittest.main()
