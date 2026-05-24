"""JUREN tracequery/out/list 解析。"""

import unittest

from youzi_v2.services.carrier_vendors import (
    _juren_query_params,
    fetch_juren_batch_for_rows,
    parse_juren_track_item,
)

SAMPLE_ITEM = {
    "jobno": "DPSECO260422040",
    "refno": "DPSECO260422040",
    "podInfoDTOList": [
        {
            "scanTime": "2026/05/19 11:16",
            "scanDatetime": 1779160560000,
            "scanStatus": "转运到货",
            "remark": "清关已放行，并抵达海外仓拆柜、分拣及预约计划需1-2个工作日",
            "scanCode": "转运到货",
            "scanStation": "ON",
            "isshow": 1,
        }
    ],
}

SAMPLE_UPS = {
    "jobno": "DPSECO260513092",
    "refno": "1Z6W639V1733861853",
    "podInfoDTOList": [
        {
            "scanTime": "2026/05/14 18:33",
            "scanDatetime": 1778754806000,
            "scanStatus": "转单",
            "remark": "转单:1Z6W639V1733861853",
            "scanCode": "TN",
            "isshow": 1,
        }
    ],
}


class JurenTrackingTest(unittest.TestCase):
    def test_query_params_newline(self) -> None:
        p = _juren_query_params({"platform": "juren"}, ["A", "B"])
        self.assertEqual(p["noList"], "A\nB")
        self.assertEqual(p["queryType"], "99")
        self.assertEqual(p["companyId"], "32")

    def test_parse_track_item(self) -> None:
        logs, cid, tn = parse_juren_track_item(SAMPLE_ITEM)
        self.assertIsNone(cid)
        self.assertEqual(tn, "DPSECO260422040")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].tracking_time, "2026-05-19 11:16:00")
        self.assertEqual(logs[0].vendor_event_id, "juren:1779160560000:转运到货")

    def test_refno_tracking_number(self) -> None:
        _, _, tn = parse_juren_track_item(SAMPLE_UPS)
        self.assertEqual(tn, "1Z6W639V1733861853")

    def test_fetch_batch_mock(self) -> None:
        import youzi_v2.services.carrier_vendors as mod

        def fake_get(nos, vendor, *, timeout):
            self.assertEqual(nos, ["DPSECO260422040"])
            return [SAMPLE_ITEM], None

        old = mod._juren_get_track
        mod._juren_get_track = fake_get
        try:
            out = fetch_juren_batch_for_rows(
                [{"shipment_no": "DPSECO260422040", "carrier_id": ""}],
                {"platform": "juren"},
            )
        finally:
            mod._juren_get_track = old
        logs, err, _, tn = out["DPSECO260422040"]
        self.assertIsNone(err)
        self.assertEqual(tn, "DPSECO260422040")
        self.assertGreater(len(logs), 0)


if __name__ == "__main__":
    unittest.main()
