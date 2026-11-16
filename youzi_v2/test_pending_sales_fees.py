import sqlite3
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from .services import pending_sales_fees as fees
from .services.order_flow_client import fetch_order_flow_rows, parse_orders_page

class PendingFeesTests(unittest.TestCase):
    def test_snapshot_isolated_and_failure_preserves_data(self):
        conn = sqlite3.connect(":memory:")
        fees.ensure_schema(conn)
        db = SimpleNamespace(conn=conn, lock=threading.RLock())
        with patch.object(fees, "fetch_order_flow_rows", return_value=[{"waybillNo": "EXAMPLE-A", "currentStatus": "pending"}]):
            self.assertEqual(fees.sync(db, Path("unused"), force=True)["remote"], 1)
        with patch.object(fees, "fetch_order_flow_rows", side_effect=ValueError("incomplete")):
            with self.assertRaises(ValueError):
                fees.sync(db, Path("unused"), force=True)
        self.assertEqual(len(fees.list_orders(db)), 1)
        with patch.object(fees, "fetch_order_flow_rows", return_value=[]):
            fees.sync(db, Path("unused"), force=True)
        self.assertEqual(fees.list_orders(db), [])
        conn.close()

    def test_invalid_pages_rejected(self):
        for body in [{"code": 200}, {"code": 200, "rows": [], "total": "bad"}, {"code": 200, "rows": [{}], "total": 1}]:
            with self.assertRaises(ValueError):
                parse_orders_page(body)

    def test_incomplete_pagination_rejected(self):
        cfg = {"authorization": "example", "url": "https://example.invalid", "page_size": 1, "method": "GET", "timeout": 5}
        response = SimpleNamespace(status_code=200, json=lambda: {"code": 200, "rows": [{"waybillNo": "EXAMPLE-A"}], "total": 2})
        with patch("youzi_v2.services.order_flow_client.require_order_flow_config", return_value=cfg), patch("youzi_v2.services.order_flow_client.requests.request", return_value=response):
            with self.assertRaises(ValueError):
                fetch_order_flow_rows(Path("unused"))

if __name__ == "__main__":
    unittest.main()
