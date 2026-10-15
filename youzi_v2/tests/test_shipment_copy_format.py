"""运单复制文案（与前端 shipmentCopyFormat 对齐）。"""

from __future__ import annotations

import unittest

from youzi_v2.services.shipment_copy_format import (
    format_shipment_detail_summary_copy_text,
    format_shipment_detail_summary_line,
    join_equals_parts,
)


class ShipmentCopyFormatTest(unittest.TestCase):
    def test_join_equals_skips_empty(self) -> None:
        self.assertEqual(
            join_equals_parts(["SN1", "", "FBA1", None, "12ctns"]),
            "SN1 = FBA1 = 12ctns",
        )

    def test_detail_summary_line(self) -> None:
        line = format_shipment_detail_summary_line(
            {
                "shipmentNo": "DPSECO260511082",
                "customerShipmentId": "FBA123",
                "addressCode": "LAS1",
                "ctns": 10,
            }
        )
        self.assertEqual(line, "DPSECO260511082 = FBA123 = LAS1 = 10ctns")

    def test_warehouse_falls_back_to_zip(self) -> None:
        line = format_shipment_detail_summary_line(
            {
                "shipmentNo": "SN1",
                "customerShipmentId": "FBA1",
                "addressCode": "",
                "zipcode": "89011",
                "ctns": 3,
            }
        )
        self.assertEqual(line, "SN1 = FBA1 = 89011 = 3ctns")

    def test_multi_row_blank_line(self) -> None:
        text = format_shipment_detail_summary_copy_text(
            [
                {"shipmentNo": "A", "customerShipmentId": "F1", "addressCode": "W1", "ctns": 1},
                {"shipmentNo": "B", "customerShipmentId": "F2", "addressCode": "W2", "ctns": 2},
            ]
        )
        self.assertEqual(text, "A = F1 = W1 = 1ctns\n\nB = F2 = W2 = 2ctns")


if __name__ == "__main__":
    unittest.main()
