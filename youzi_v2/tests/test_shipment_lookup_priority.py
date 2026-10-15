"""运单 lookup 优先级：运单号 → 货件号 → 客户编号。"""

from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.shipments_table import TABLE_NAME, ensure_schema as ensure_shipments_schema


class ShipmentLookupPriorityTest(unittest.TestCase):
    def test_priority_order(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        ensure_shipments_schema(db.conn)
        now = now_str()
        with db.lock:
            db.conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, shipment_no, customer_no, customer_shipment_id,
                    status_code, tracking_log_count, created_time, updated_time
                ) VALUES (?, ?, ?, ?, 'IN_TRANSIT', 0, ?, ?)
                """,
                (str(uuid.uuid4()), "SN-1", "CUST-99", "FBA-ABC", now, now),
            )
            db.conn.commit()
        repo = ShipmentsRepository(db)
        by_sn = repo.get_by_lookup_priority("SN-1")
        self.assertEqual(by_sn and by_sn.get("shipmentNo"), "SN-1")
        by_fba = repo.get_by_lookup_priority("FBA-ABC")
        self.assertEqual(by_fba and by_fba.get("shipmentNo"), "SN-1")
        by_cust = repo.get_by_lookup_priority("CUST-99")
        self.assertEqual(by_cust and by_cust.get("shipmentNo"), "SN-1")
        self.assertIsNone(repo.get_by_lookup_priority("MISSING"))
        db.conn.close()
        tmp.cleanup()

    def test_shipment_id_beats_customer_no_even_if_older(self) -> None:
        """货件号命中优先于客户编号，不因 updated_time 新而颠倒。"""
        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        ensure_shipments_schema(db.conn)
        now = now_str()
        with db.lock:
            db.conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, shipment_no, customer_no, customer_shipment_id,
                    status_code, tracking_log_count, created_time, updated_time
                ) VALUES (?, ?, ?, ?, 'IN_TRANSIT', 0, ?, ?)
                """,
                (str(uuid.uuid4()), "SN-NEW-CUST", "SHARED-KEY", "OTHER-FBA", now, now),
            )
            db.conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, shipment_no, customer_no, customer_shipment_id,
                    status_code, tracking_log_count, created_time, updated_time
                ) VALUES (?, ?, ?, ?, 'IN_TRANSIT', 0, '2000-01-01 00:00:00', '2000-01-01 00:00:00')
                """,
                (str(uuid.uuid4()), "SN-FBA-HIT", "X", "SHARED-KEY"),
            )
            db.conn.commit()
        repo = ShipmentsRepository(db)
        hit = repo.get_by_lookup_priority("SHARED-KEY")
        self.assertEqual(hit and hit.get("shipmentNo"), "SN-FBA-HIT")
        db.conn.close()
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
