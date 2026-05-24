"""HAOJIE trackList 解析（与 OLT 同型）。"""

import unittest

from youzi_v2.services.carrier_vendors import (
    _tracklist_api_url,
    fetch_haojie_batch_for_rows,
    parse_olt_track_item,
)

SAMPLE = {
    "showcustomernumber1": "DPSECO251111037",
    "pkid": 267281,
    "customernumber1": "DPSECO251111037",
    "systemnumber": "42016217159",
    "showtracknumber": "RCD26000781219",
    "outdate": "2026-03-20 13:13:12",
    "outinfo": "澳洲海关放行 Shipment cleared(CLEAR)",
    "outdesc": "",
    "tracknumber": "RCD26000781219",
}


class HaojieTrackingTest(unittest.TestCase):
    def test_default_api_url(self) -> None:
        self.assertEqual(
            _tracklist_api_url({"platform": "haojie"}),
            "http://120.24.174.13:8180/trackList",
        )

    def test_parse_item(self) -> None:
        logs, cid, tn = parse_olt_track_item(SAMPLE, {"platform": "haojie"})
        self.assertEqual(cid, "42016217159")
        self.assertEqual(tn, "RCD26000781219")
        self.assertEqual(logs[0].vendor_event_id, "haojie:267281")

    def test_fetch_batch_mock(self) -> None:
        import youzi_v2.services.carrier_vendors as mod

        def fake_post(nos, vendor, *, timeout):
            return [SAMPLE], None

        old = mod._olt_post_track
        mod._olt_post_track = fake_post
        try:
            out = fetch_haojie_batch_for_rows(
                [{"shipment_no": "DPSECO251111037", "carrier_id": ""}],
                {"platform": "haojie"},
            )
        finally:
            mod._olt_post_track = old
        logs, err, cid, tn = out["DPSECO251111037"]
        self.assertIsNone(err)
        self.assertEqual(cid, "42016217159")
        self.assertGreater(len(logs), 0)


if __name__ == "__main__":
    unittest.main()
