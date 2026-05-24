"""WY getPublicLogisticsTrackList 解析。"""

import unittest

from youzi_v2.services.carrier_vendors import (
    _wy_request_headers,
    _wy_target_shipments,
    fetch_wy_batch_for_rows,
    parse_wy_track_group,
)

SAMPLE_GROUP = {
    "customerOrderNumber": "DPSECO260418047",
    "systemOrderNumber": "DPSECO260418047",
    "list": [
        {
            "status": "干线运输",
            "childNodeList": [
                {
                    "id": "2055472557515083830",
                    "nodeName": "开船",
                    "nodeTime": "2026/05/15 15:00",
                    "nodeDesc": "已开船，起运地NINGBO",
                }
            ],
        },
        {
            "status": "新订单",
            "childNodeList": [
                {
                    "id": "2055472557515083838",
                    "nodeName": "下单成功",
                    "nodeTime": "2026/04/30 18:30",
                    "nodeDesc": "您已下单",
                }
            ],
        },
    ],
}


class WyTrackingTest(unittest.TestCase):
    def test_request_headers_authorization(self) -> None:
        h = _wy_request_headers({"platform": "wy", "authorization": "Bearer test"})
        self.assertEqual(h["authorization"], "Bearer test")

    def test_parse_track_group(self) -> None:
        logs, cid, tn = parse_wy_track_group(SAMPLE_GROUP)
        self.assertEqual(cid, "DPSECO260418047")
        self.assertIsNone(tn)
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].vendor_event_id, "wy:2055472557515083830")
        self.assertEqual(logs[0].tracking_time, "2026-05-15 15:00:00")
        self.assertIn("开船", logs[0].tracking_desc)

    def test_target_shipments(self) -> None:
        order_to_sns = {"DPSECO260418047": {"DPSECO260418047"}}
        targets = _wy_target_shipments(SAMPLE_GROUP, order_to_sns, {"DPSECO260418047"})
        self.assertEqual(targets, {"DPSECO260418047"})

    def test_fetch_batch_mock(self) -> None:
        import youzi_v2.services.carrier_vendors as mod

        def fake_post(order_list, vendor, *, timeout):
            self.assertEqual(order_list, ["DPSECO260418047"])
            return [SAMPLE_GROUP], None

        old = mod._wy_post_track
        mod._wy_post_track = fake_post
        try:
            out = fetch_wy_batch_for_rows(
                [{"shipment_no": "DPSECO260418047", "carrier_id": ""}],
                {"platform": "wy", "authorization": "x"},
            )
        finally:
            mod._wy_post_track = old
        logs, err, cid, _ = out["DPSECO260418047"]
        self.assertIsNone(err)
        self.assertEqual(cid, "DPSECO260418047")
        self.assertGreater(len(logs), 0)


if __name__ == "__main__":
    unittest.main()
