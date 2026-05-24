"""QIYUN WebTrack XML 解析。"""

import unittest
import xml.etree.ElementTree as ET

from youzi_v2.services.carrier_vendors import (
    _qiyun_form_body,
    _qiyun_parse_xml,
    _qiyun_request_headers,
    fetch_qiyun_batch_for_rows,
    parse_qiyun_track_element,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<xdoc>
  <xout>
    <track index="0" billid="QY06015307BWU2" transbillid="QY06015307BWU2" refernum="DPSECO260403263">
      <trackitem index="trackitem_0_0" sdate="2026-05-10 09:47:41" place="澳大利亚" intro="清关已放行" />
      <trackitem index="trackitem_0_1" sdate="2026-05-10 09:47:31" place="澳大利亚" intro="已经拆柜完毕，等待下一步操作" />
    </track>
  </xout>
</xdoc>"""


class QiyunTrackingTest(unittest.TestCase):
    def test_form_body(self) -> None:
        body = _qiyun_form_body("DPSECO260403262", {"platform": "qiyun"})
        self.assertEqual(body["billid"], "DPSECO260403262")
        self.assertEqual(body["index"], "0")
        self.assertEqual(body["isRepeat"], "no")

    def test_cookie_header_from_config_key(self) -> None:
        h = _qiyun_request_headers(
            {"platform": "qiyun", "Cookie": "JSESSIONID=abc; JSESSIONID=def"}
        )
        self.assertEqual(h["Cookie"], "JSESSIONID=abc; JSESSIONID=def")

    def test_parse_track_element(self) -> None:
        root = ET.fromstring(SAMPLE_XML)
        track = root.find(".//track")
        assert track is not None
        logs, cid, tn = parse_qiyun_track_element(track, expected_sn="DPSECO260403263")
        self.assertEqual(cid, "QY06015307BWU2")
        self.assertEqual(tn, "QY06015307BWU2")
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].vendor_event_id, "qiyun:trackitem_0_0")

    def test_parse_xml_match_refernum(self) -> None:
        logs, cid, tn, err = _qiyun_parse_xml(SAMPLE_XML, "DPSECO260403263")
        self.assertIsNone(err)
        self.assertEqual(cid, "QY06015307BWU2")
        self.assertEqual(len(logs), 2)

    def test_empty_shell_without_session(self) -> None:
        shell = """<?xml version="1.0" encoding="UTF-8"?>
<xdoc><xout><track index="1" billid="DPSECO260403263" /></xout></xdoc>"""
        logs, cid, tn, err = _qiyun_parse_xml(shell, "DPSECO260403263")
        self.assertEqual(len(logs), 0)
        self.assertIsNone(cid)
        self.assertIsNotNone(err)
        self.assertIn("Cookie", err or "")

    def test_fetch_batch_mock(self) -> None:
        import youzi_v2.services.carrier_vendors as mod

        def fake_one(sn, vendor, *, timeout):
            return _qiyun_parse_xml(SAMPLE_XML, "DPSECO260403263")

        old = mod._qiyun_fetch_one
        mod._qiyun_fetch_one = fake_one
        try:
            out = fetch_qiyun_batch_for_rows(
                [{"shipment_no": "DPSECO260403263", "carrier_id": ""}],
                {"platform": "qiyun"},
            )
        finally:
            mod._qiyun_fetch_one = old
        logs, err, cid, tn = out["DPSECO260403263"]
        self.assertIsNone(err)
        self.assertEqual(cid, "QY06015307BWU2")
        self.assertGreater(len(logs), 0)


if __name__ == "__main__":
    unittest.main()
