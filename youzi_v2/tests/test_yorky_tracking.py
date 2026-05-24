"""聚美 56yorky trackInfo 解析。"""

import unittest

from youzi_v2.services.carrier_vendors import (
    fetch_yorky_batch_for_rows,
    parse_yorky_track_item,
)

SAMPLE_ITEM = {
    "userNo": "DPSECO260511082",
    "trackNo": "871692280770",
    "trackInfoList": [
        {
            "id": 411764,
            "trackTime": "2026-05-21 00:00:00",
            "trackDesc": "已交UPS/FEDEX，请留意官网更新",
            "trackStatusText": "已交付快递",
        }
    ],
}

SAMPLE_EMPTY_TRACKS = {
    "userNo": "DPSECO260519152",
    "trackNo": "872151463022",
    "trackInfoList": [],
    "inputChanges": [
        {
            "changeSn": 12934680,
            "busiCode": "已确认",
            "createTime": "2026-05-23 09:32:07",
            "remark": "直接确认",
        }
    ],
}


class YorkyTrackingTest(unittest.TestCase):
    def test_parse_track_item(self) -> None:
        logs, cid, tn = parse_yorky_track_item(SAMPLE_ITEM)
        self.assertIsNone(cid)
        self.assertEqual(tn, "871692280770")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].vendor_event_id, "yorky:t:411764")

    def test_fallback_input_changes(self) -> None:
        logs, _, tn = parse_yorky_track_item(SAMPLE_EMPTY_TRACKS)
        self.assertEqual(tn, "872151463022")
        self.assertEqual(len(logs), 1)
        self.assertIn("已确认", logs[0].tracking_desc)

    def test_fetch_batch_mock(self) -> None:
        import youzi_v2.services.carrier_vendors as mod

        def fake_get(track_nos, vendor, *, timeout):
            self.assertEqual(track_nos, ["DPSECO260511082"])
            return [SAMPLE_ITEM], None

        old = mod._yorky_get_track
        mod._yorky_get_track = fake_get
        try:
            out = fetch_yorky_batch_for_rows(
                [{"shipment_no": "DPSECO260511082", "carrier_id": ""}],
                {"platform": "yorky"},
            )
        finally:
            mod._yorky_get_track = old
        logs, err, _, tn = out["DPSECO260511082"]
        self.assertIsNone(err)
        self.assertEqual(tn, "871692280770")
        self.assertGreater(len(logs), 0)


if __name__ == "__main__":
    unittest.main()
