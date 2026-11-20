from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from youzi_v2.services.shipment_dps_mapper import dps_row_to_shipment
from youzi_v2.services.shipment_remarks import update_shipment_remarks


class _Response:
    status_code = 200


class _Repo:
    def __init__(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE shipments (id TEXT PRIMARY KEY, remark TEXT, updated_time TEXT)")
        conn.executemany(
            "INSERT INTO shipments VALUES (?, ?, '')",
            [("a", "旧备注 A"), ("b", "旧备注 B")],
        )
        self._database = SimpleNamespace(conn=conn, lock=_Lock())
        self.rows = {
            "a": {"id": "a", "shipmentNo": "TEST-A", "waybillId": "101", "statusCode": "0", "remark": "旧备注 A"},
            "b": {"id": "b", "shipmentNo": "TEST-B", "waybillId": "102", "statusCode": "1", "remark": "旧备注 B"},
        }

    def get_by_id(self, item_id):
        return self.rows.get(item_id)


class _Lock:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class ShipmentRemarksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp.name) / "config.json"
        self.config_path.write_text(
            json.dumps({"dps_authorization": "Bearer test", "dps_updateRemark": {"url": "https://example.test/update"}}),
            encoding="utf-8",
        )
        self.repo = _Repo()

    def tearDown(self):
        self.repo._database.conn.close()
        self.temp.cleanup()

    @patch("youzi_v2.services.shipment_remarks.requests.request", return_value=_Response())
    def test_batch_uses_one_remote_request_and_overwrites_local(self, request):
        result = update_shipment_remarks(self.repo, self.config_path, ["a", "b"], "新备注\r\n第二行")

        self.assertEqual(result, {"total": 2, "updated": 2, "failed": 0})
        self.assertEqual(
            request.call_args.kwargs["json"],
            {"remark": "新备注\n第二行", "commerceWaybillIds": ["101", "102"]},
        )
        self.assertEqual(request.call_args.args[:2], ("PUT", "https://example.test/update"))
        self.assertFalse(request.call_args.kwargs["allow_redirects"])
        values = self.repo._database.conn.execute("SELECT id, remark FROM shipments ORDER BY id").fetchall()
        self.assertEqual(values, [("a", "新备注\n第二行"), ("b", "新备注\n第二行")])

    @patch("youzi_v2.services.shipment_remarks.requests.request")
    def test_only_http_200_updates_local_remarks(self, request):
        for status_code in (202, 204, 302, 500):
            with self.subTest(status_code=status_code):
                request.return_value = SimpleNamespace(status_code=status_code)
                with self.assertRaisesRegex(ValueError, f"HTTP {status_code}"):
                    update_shipment_remarks(self.repo, self.config_path, ["a"], "新备注")
                value = self.repo._database.conn.execute("SELECT remark FROM shipments WHERE id='a'").fetchone()[0]
                self.assertEqual(value, "旧备注 A")

    @patch("youzi_v2.services.shipment_remarks.requests.request", return_value=_Response())
    def test_missing_waybill_is_rejected_before_request(self, request):
        self.repo.rows["a"]["waybillId"] = ""
        with self.assertRaisesRegex(ValueError, "缺少 DPS ID"):
            update_shipment_remarks(self.repo, self.config_path, ["a"], "新备注")
        request.assert_not_called()

    def test_dps_mapper_preserves_multiline_remark_and_remote_clear(self):
        mapped = dps_row_to_shipment({"odd": "TEST-A", "remark": "第一行\n第二行"})
        cleared = dps_row_to_shipment({"odd": "TEST-B", "remark": ""})

        self.assertEqual(mapped["remark"], "第一行\n第二行")
        self.assertEqual(cleared["remark"], "")


if __name__ == "__main__":
    unittest.main()
