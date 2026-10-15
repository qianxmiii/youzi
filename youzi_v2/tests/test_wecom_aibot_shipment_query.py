"""企业微信运单号解析与回复文案。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from youzi_v2.services.wecom_aibot_shipment_query import (
    _customer_ref_lines,
    build_shipment_query_reply,
    extract_callback_text,
    extract_lookup_keys,
    extract_shipment_nos,
    format_shipment_status_block,
    message_wants_detail_summary,
)


class WecomAibotShipmentQueryTest(unittest.TestCase):
    def test_extract_dps_shipment_nos(self) -> None:
        text = "帮忙看下 DPSECO260511082 和 dpseco260519152 谢谢"
        nos = extract_shipment_nos(text)
        self.assertEqual(nos, ["DPSECO260511082", "DPSECO260519152"])

    def test_extract_single_token_fallback(self) -> None:
        self.assertEqual(extract_shipment_nos("DPSECO260511082"), ["DPSECO260511082"])

    def test_extract_fba_and_strip_at(self) -> None:
        keys = extract_lookup_keys("@柚子机器人 FBA19FN8FN6C")
        self.assertEqual(keys, ["FBA19FN8FN6C"])

    def test_message_wants_detail_summary(self) -> None:
        self.assertTrue(message_wants_detail_summary("DPSECO1 运单明细"))
        self.assertFalse(message_wants_detail_summary("DPSECO260511082"))

    @patch("youzi_v2.services.wecom_aibot_shipment_query.read_shipment_query_refresh_enabled", return_value=False)
    @patch("youzi_v2.services.wecom_aibot_shipment_query.refresh_shipment_for_wecom_query")
    def test_build_reply_detail_summary(self, _mock_refresh, _mock_flag) -> None:
        class FakeRepo:
            def get_by_lookup_priority(self, no: str):
                return {
                    "shipmentNo": no,
                    "customerShipmentId": "FBA-X",
                    "addressCode": "LAS1",
                    "ctns": 5,
                }

            def get_by_shipment_no(self, no: str):
                return None

        reply = build_shipment_query_reply(
            "查明细 DPSECO260511082",
            repo=FakeRepo(),  # type: ignore[arg-type]
        )
        self.assertEqual(reply, "DPSECO260511082 = FBA-X = LAS1 = 5ctns")
        self.assertNotIn("转运状态", reply)
        _mock_refresh.assert_not_called()

    def test_extract_callback_text(self) -> None:
        frame = {
            "body": {
                "msgtype": "text",
                "text": {"content": " DPSECO260511082 "},
            }
        }
        self.assertEqual(extract_callback_text(frame), "DPSECO260511082")

    def test_format_block(self) -> None:
        block = format_shipment_status_block(
            {
                "shipmentNo": "DPSECO260511082",
                "customer": "测试客户",
                "customerNo": "CNO-1",
                "customerShipmentId": "FBA123",
                "channelNameZh": "海卡",
                "routeStatus": "ARRIVED_POD",
                "statusCode": "IN_TRANSIT",
                "latestTrackingDesc": "已到港",
                "latestTrackingTime": "2026-06-01 10:00:00",
                "latestCarrierDesc": "In transit",
                "latestCarrierTime": "2026-06-02 08:30:00",
                "addressCode": "LAS1",
                "zipcode": "89011",
                "ctns": 12,
                "trackingNumber": "1Z999",
            }
        )
        self.assertIn("【DPSECO260511082】", block)
        self.assertIn("客户编号：CNO-1", block)
        self.assertIn("货件号：FBA123", block)
        self.assertIn("到达目的港", block)
        self.assertIn("最新内部轨迹：已到港", block)
        self.assertIn("轨迹时间：2026-06-01 10:00", block)
        self.assertIn("转运状态：转运中", block)
        self.assertIn("明细状态：到达目的港", block)
        self.assertIn("派送仓库：LAS1", block)
        self.assertIn("转单号：1Z999", block)

    def test_customer_no_dedup_with_shipment_id(self) -> None:
        row = {"customerNo": "FBA123", "customerShipmentId": "fba123"}
        lines = _customer_ref_lines(row)
        self.assertEqual(lines, ["货件号：fba123"])

    def test_customer_no_and_shipment_id_differ(self) -> None:
        row = {"customerNo": "ORD-1", "customerShipmentId": "FBA123"}
        lines = _customer_ref_lines(row)
        self.assertEqual(len(lines), 2)

    def test_omit_empty_fields(self) -> None:
        block = format_shipment_status_block(
            {
                "shipmentNo": "DPSECO1",
                "statusCode": "IN_TRANSIT",
            }
        )
        self.assertIn("【DPSECO1】", block)
        self.assertIn("转运状态：转运中", block)
        self.assertNotIn("客户：", block)
        self.assertNotIn("货件号：", block)
        self.assertNotIn("转单号：", block)
        self.assertNotIn("—", block)

    @patch("youzi_v2.services.wecom_aibot_shipment_query.read_shipment_query_refresh_enabled", return_value=False)
    @patch("youzi_v2.services.wecom_aibot_shipment_query.refresh_shipment_for_wecom_query")
    def test_build_reply_skips_refresh_when_disabled(
        self, _mock_refresh, _mock_flag
    ) -> None:
        from youzi_v2.services.wecom_aibot_shipment_query import build_shipment_query_reply

        class FakeRepo:
            def get_by_lookup_priority(self, no: str):
                return {
                    "shipmentNo": no,
                    "customer": "x",
                    "statusCode": "IN_TRANSIT",
                }

        build_shipment_query_reply("DPSECO260511082", repo=FakeRepo())  # type: ignore[arg-type]
        _mock_refresh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
