"""运单追踪号表。"""

import tempfile
import unittest
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.shipment_tracking_numbers_repository import ShipmentTrackingNumbersRepository
from youzi_v2.db.shipment_tracking_numbers_table import ensure_schema


class ShipmentTrackingNumbersRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        ensure_schema(self.db.conn)
        self.repo = ShipmentTrackingNumbersRepository(self.db)

    def tearDown(self) -> None:
        self.db.conn.close()
        self.tmp.cleanup()

    def test_replace_includes_main_as_sub(self) -> None:
        n = self.repo.replace_for_shipment(
            "DPSECO260410140",
            "870833728471",
            ["870833728471", "870833728482"],
        )
        self.assertEqual(n, 2)
        rows = self.repo.list_by_shipment_no("DPSECO260410140")
        mains = [r for r in rows if r["isMain"]]
        self.assertEqual(len(mains), 1)
        self.assertEqual(mains[0]["trackingNumber"], "870833728471")


if __name__ == "__main__":
    unittest.main()
