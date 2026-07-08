"""WY getPublicLogisticsTrackList 解析。"""

import unittest

from youzi_v2.services.carrier_vendors import (
    _wy_api_url,
    _wy_extract_track_groups,
    _wy_post_track,
    _wy_request_headers,
    _wy_target_shipments,
    fetch_wy_batch_for_rows,
    parse_wy_track_group,
    wy_should_update_carrier_order_no,
)

SAMPLE_GROUP = {
    "customerOrderNumber": "DPSECO260529171",
    "systemOrderNumber": "WYNVWFPS7SS",
    "list": [
        {
            "status": "干线运输",
            "childNodeList": [
                {
                    "id": "2074761435761610754",
                    "nodeName": "开船",
                    "nodeTime": "2026/06/19 15:15",
                    "nodeDesc": "已开船，起运地NINGBO",
                }
            ],
        },
        {
            "status": "新订单",
            "childNodeList": [
                {
                    "id": "2074761435761610762",
                    "nodeName": "下单成功",
                    "nodeTime": "2026/06/06 11:24",
                    "nodeDesc": "您已下单",
                }
            ],
        },
    ],
}


class WyTrackingTest(unittest.TestCase):
    def test_api_url(self) -> None:
        vendor = {
            "apiUrl": "http://www.wy-express.com/root-api/c/order/getPublicLogisticsTrackList",
        }
        self.assertEqual(_wy_api_url(vendor), vendor["apiUrl"])

    def test_extract_track_list(self) -> None:
        payload = {"trackList": [SAMPLE_GROUP]}
        groups = _wy_extract_track_groups(payload)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["systemOrderNumber"], "WYNVWFPS7SS")

    def test_request_headers_authorization(self) -> None:
        h = _wy_request_headers({"platform": "wy", "authorization": "Bearer test"})
        self.assertEqual(h["authorization"], "Bearer test")

    def test_parse_track_group(self) -> None:
        logs, carrier_order_no, tn = parse_wy_track_group(SAMPLE_GROUP)
        self.assertEqual(carrier_order_no, "WYNVWFPS7SS")
        self.assertIsNone(tn)
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].vendor_event_id, "wy:2074761435761610754")
        self.assertEqual(logs[0].tracking_time, "2026-06-19 15:15:00")
        self.assertIn("开船", logs[0].tracking_desc)

    def test_should_update_carrier_order_no(self) -> None:
        self.assertTrue(
            wy_should_update_carrier_order_no("DPSECO260529171", "WYNVWFPS7SS", "DPSECO260529171")
        )
        self.assertFalse(
            wy_should_update_carrier_order_no("WYNVWFPS7SS", "WYNVWFPS7SS", "DPSECO260529171")
        )
        self.assertTrue(wy_should_update_carrier_order_no("", "WYNVWFPS7SS", "DPSECO260529171"))

    def test_target_shipments(self) -> None:
        order_to_sns = {"DPSECO260529171": {"DPSECO260529171"}}
        targets = _wy_target_shipments(SAMPLE_GROUP, order_to_sns, {"DPSECO260529171"})
        self.assertEqual(targets, {"DPSECO260529171"})

    def test_post_track_request_body(self) -> None:
        import json as json_mod

        import youzi_v2.services.carrier_vendors as mod

        captured: dict[str, object] = {}
        payload_bytes = json_mod.dumps(
            {"code": 200, "data": {"trackList": [SAMPLE_GROUP]}},
            ensure_ascii=False,
        ).encode("utf-8")

        class FakeResp:
            status_code = 200
            content = payload_bytes

        def fake_post(url, *, json, headers, timeout, verify):
            captured["json"] = json
            return FakeResp()

        old_post = mod.requests.post
        mod.requests.post = fake_post
        try:
            groups, err = _wy_post_track(
                ["DPSECO260529171"],
                {"platform": "wy", "authorization": "x", "apiUrl": "http://example/track"},
                timeout=10,
            )
        finally:
            mod.requests.post = old_post
        self.assertIsNone(err)
        self.assertEqual(len(groups), 1)
        body = captured["json"]
        assert isinstance(body, dict)
        self.assertEqual(body, {"customerOrderNumberList": ["DPSECO260529171"]})
        self.assertNotIn("orderIdList", body)

    def test_fetch_batch_mock(self) -> None:
        import youzi_v2.services.carrier_vendors as mod

        def fake_post(order_list, vendor, *, timeout):
            self.assertEqual(order_list, ["DPSECO260529171"])
            return [SAMPLE_GROUP], None

        old = mod._wy_post_track
        mod._wy_post_track = fake_post
        try:
            out = fetch_wy_batch_for_rows(
                [{"shipment_no": "DPSECO260529171", "carrier_id": ""}],
                {"platform": "wy", "authorization": "x"},
            )
        finally:
            mod._wy_post_track = old
        logs, err, carrier_order_no, _ = out["DPSECO260529171"]
        self.assertIsNone(err)
        self.assertEqual(carrier_order_no, "WYNVWFPS7SS")
        self.assertGreater(len(logs), 0)


if __name__ == "__main__":
    unittest.main()
