"""DPS 清关细状态 → 自动开/关异常。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.shipment_exception_events_repository import (
    ShipmentExceptionEventsRepository,
)
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.services.shipment_route_status_exception import (
    apply_customs_exception_from_route_status,
)


class RouteStatusCustomsExceptionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        self.shipments = ShipmentsRepository(self.db)
        self.exc = ShipmentExceptionEventsRepository(self.db)
        row, _ = self.shipments.upsert_by_shipment_no(
            {
                "shipment_no": "DPS-CUSTOMS-1",
                "status_code": "IN_TRANSIT",
                "route_status": "WAREHOUSE_IN",
            }
        )
        self.shipment_no = row["shipmentNo"]

    def tearDown(self) -> None:
        self.db.conn.close()
        self.tmp.cleanup()

    def test_open_on_export_customs_exception(self) -> None:
        result = apply_customs_exception_from_route_status(
            self.db,
            self.shipment_no,
            "EXPORT_CUSTOMS_EXCEPTION",
        )
        self.assertEqual(result["action"], "opened")
        ship = self.shipments.get_by_shipment_no(self.shipment_no)
        assert ship is not None
        self.assertEqual(ship["exceptionCode"], "EXPORT_CUSTOMS_EXCEPTION")

    def test_switch_export_to_import(self) -> None:
        apply_customs_exception_from_route_status(
            self.db, self.shipment_no, "EXPORT_CUSTOMS_EXCEPTION"
        )
        result = apply_customs_exception_from_route_status(
            self.db, self.shipment_no, "IMPORT_CUSTOMS_EXCEPTION"
        )
        self.assertEqual(result["action"], "opened")
        ship = self.shipments.get_by_shipment_no(self.shipment_no)
        assert ship is not None
        self.assertEqual(ship["exceptionCode"], "IMPORT_CUSTOMS_EXCEPTION")

    def test_close_when_later_milestone(self) -> None:
        apply_customs_exception_from_route_status(
            self.db, self.shipment_no, "IMPORT_CUSTOMS_EXCEPTION"
        )
        result = apply_customs_exception_from_route_status(
            self.db, self.shipment_no, "DEST_TRANSIT_WAREHOUSE"
        )
        self.assertEqual(result["action"], "closed")
        ship = self.shipments.get_by_shipment_no(self.shipment_no)
        assert ship is not None
        self.assertFalse(ship.get("exceptionCode"))

    def test_do_not_close_manual_lost(self) -> None:
        self.exc.open_for_shipment_nos([self.shipment_no], "LOST", note="manual")
        result = apply_customs_exception_from_route_status(
            self.db, self.shipment_no, "ARRIVED_POD"
        )
        self.assertEqual(result["action"], "noop")
        ship = self.shipments.get_by_shipment_no(self.shipment_no)
        assert ship is not None
        self.assertEqual(ship["exceptionCode"], "LOST")

    def test_do_not_open_over_manual_lost(self) -> None:
        self.exc.open_for_shipment_nos([self.shipment_no], "LOST", note="manual")
        result = apply_customs_exception_from_route_status(
            self.db, self.shipment_no, "EXPORT_CUSTOMS_EXCEPTION"
        )
        self.assertEqual(result["action"], "skip")
        ship = self.shipments.get_by_shipment_no(self.shipment_no)
        assert ship is not None
        self.assertEqual(ship["exceptionCode"], "LOST")


if __name__ == "__main__":
    unittest.main()
