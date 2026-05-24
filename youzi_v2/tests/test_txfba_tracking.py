"""TX getOrderTrackDetailList 解析。"""

import unittest

from youzi_v2.services.carrier_vendors import (
    _txfba_request_headers,
    _txfba_target_shipments,
    fetch_txfba_batch_for_rows,
    parse_txfba_detail_group,
)

SAMPLE_GROUP = {
    "billNo": "ICBU00001035096",
    "trackList": [
        {
            "billTrackNo": "2058138316319911938",
            "billNo": "ICBU00001035096",
            "trackInfo": "[预计]官网最新显示预计2026-05-31 13:00:00到港。XIN YA ZHOU 175E",
            "trackTime": "2026-05-23 18:49:47",
            "trackName": "预计到港",
            "customerBillNo": "DPSECO260416086",
            "expressMainNo": None,
        },
        {
            "billTrackNo": "2045385766925799426",
            "trackTime": "2026-04-18 14:15:42",
            "trackInfo": "客户已下单提交预报",
            "trackName": "提交预报",
            "customerBillNo": "DPSECO260416086",
            "expressMainNo": "1Z999AA10123456784",
        },
    ],
}


class TxfbaTrackingTest(unittest.TestCase):
    def test_request_headers_include_ownersystem(self) -> None:
        h = _txfba_request_headers({"platform": "txfba"})
        self.assertEqual(h["ownersystem"], "EMPLOYEE_TERMINAL")

    def test_parse_detail_group(self) -> None:
        logs, cid, tn = parse_txfba_detail_group(SAMPLE_GROUP)
        self.assertEqual(cid, "ICBU00001035096")
        self.assertEqual(tn, "1Z999AA10123456784")
        self.assertGreaterEqual(len(logs), 2)
        self.assertEqual(logs[0].vendor_event_id, "txfba:2058138316319911938")
        self.assertIn("预计到港", logs[0].tracking_desc)

    def test_target_shipments_by_customer_bill_no(self) -> None:
        bill_to_sns = {"DPSECO260416086": {"DPSECO260416086"}}
        pending = {"DPSECO260416086"}
        targets = _txfba_target_shipments(SAMPLE_GROUP, bill_to_sns, pending)
        self.assertEqual(targets, {"DPSECO260416086"})

    def test_fetch_batch_mock(self) -> None:
        import youzi_v2.services.carrier_vendors as mod

        def fake_post(bill_list, vendor, *, timeout):
            self.assertEqual(bill_list, ["DPSECO260416086"])
            return [SAMPLE_GROUP], None

        old = mod._txfba_post_detail
        mod._txfba_post_detail = fake_post
        try:
            out = fetch_txfba_batch_for_rows(
                [{"shipment_no": "DPSECO260416086", "carrier_id": ""}],
                {"platform": "txfba"},
            )
        finally:
            mod._txfba_post_detail = old
        logs, err, cid, tn = out["DPSECO260416086"]
        self.assertIsNone(err)
        self.assertEqual(cid, "ICBU00001035096")
        self.assertEqual(tn, "1Z999AA10123456784")
        self.assertGreater(len(logs), 0)


if __name__ == "__main__":
    unittest.main()
