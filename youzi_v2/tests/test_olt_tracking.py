"""OLT trackList 解析。"""

import unittest

from youzi_v2.services.carrier_vendors import (
    _olt_form_body,
    _olt_shipment_nos_from_item,
    fetch_olt_batch_for_rows,
    parse_olt_track_item,
)

SAMPLE_A = {
    "showcustomernumber1": "DPSECO260430120",
    "pkid": 274580,
    "customernumber1": "DPSECO260430120",
    "systemnumber": "260507237262",
    "showtracknumber": "1ZA06B016814294090",
    "outdate": "2026-05-22 10:28:29",
    "outinfo": "已递送 ",
    "outdesc": "SE  AARSTA",
    "tracknumber": "1ZA06B016814294090",
    "status": "signed",
}

SAMPLE_B = {
    "showcustomernumber1": "DPSECO260423181",
    "pkid": 269704,
    "customernumber1": "DPSECO260423181",
    "systemnumber": "260424348531",
    "showtracknumber": "1ZA06B016826679232",
    "outdate": "2026-05-22 13:48:24",
    "outinfo": "已递送 ",
    "outdesc": "ES  CEHEGIN",
    "tracknumber": "1ZA06B016826679232",
    "status": "signing",
}


class OltTrackingTest(unittest.TestCase):
    def test_form_body(self) -> None:
        body = _olt_form_body(["DPSECO260430120", "DPSECO260423181"], {"platform": "olt"})
        self.assertIn("DPSECO260430120\nDPSECO260423181", body["searchList.waybillnumber"])
        self.assertEqual(body["searchLang"], "zh")

    def test_parse_item(self) -> None:
        logs, cid, tn = parse_olt_track_item(SAMPLE_A, {"platform": "olt"})
        self.assertEqual(cid, "260507237262")
        self.assertEqual(tn, "1ZA06B016814294090")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].vendor_event_id, "olt:274580")
        self.assertIn("已递送", logs[0].tracking_desc)

    def test_shipment_keys(self) -> None:
        self.assertEqual(_olt_shipment_nos_from_item(SAMPLE_B), {"DPSECO260423181"})

    def test_fetch_batch_mock(self) -> None:
        import youzi_v2.services.carrier_vendors as mod

        def fake_post(nos, vendor, *, timeout):
            self.assertEqual(len(nos), 2)
            return [SAMPLE_A, SAMPLE_B], None

        old = mod._olt_post_track
        mod._olt_post_track = fake_post
        try:
            out = fetch_olt_batch_for_rows(
                [
                    {"shipment_no": "DPSECO260430120", "carrier_id": ""},
                    {"shipment_no": "DPSECO260423181", "carrier_id": ""},
                ],
                {"platform": "olt"},
            )
        finally:
            mod._olt_post_track = old
        logs_a, err_a, cid_a, tn_a = out["DPSECO260430120"]
        self.assertIsNone(err_a)
        self.assertEqual(cid_a, "260507237262")
        self.assertEqual(tn_a, "1ZA06B016814294090")
        self.assertGreater(len(logs_a), 0)


if __name__ == "__main__":
    unittest.main()
