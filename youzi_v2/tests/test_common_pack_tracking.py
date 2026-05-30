"""XKP common_pack / 华威尔 报文字段回写。"""

import unittest

from youzi_v2.services.carrier_vendors import (
    _common_pack_ids_from_data,
    _common_pack_sub_zycodes,
    _common_pack_tracking_bundle,
)


class CommonPackTrackingTest(unittest.TestCase):
    def test_orderno_and_outer_zycode(self) -> None:
        data = {
            "orderno": "ICBU00001036120",
            "zycode": "1Z999AA10123456784",
            "kdzt": "转运中",
            "details": [{"zztm": "2026-05-01 12:00:00", "guiji": "已收货"}],
        }
        cid, tn, all_tns = _common_pack_ids_from_data(data)
        self.assertEqual(cid, "ICBU00001036120")
        self.assertEqual(tn, "1Z999AA10123456784")
        self.assertEqual(all_tns, ["1Z999AA10123456784"])

    def test_inner_zycode_as_sub_tracking(self) -> None:
        data = {
            "orderno": "HW260501",
            "zycode": "1Z999AA10123456784",
            "details": [
                {
                    "zycode": "SUB001",
                    "zztm": "2026-05-01 12:00:00",
                    "guiji": "已收货",
                },
                {
                    "zycode": "SUB002",
                    "zztm": "2026-05-02 08:00:00",
                    "guiji": "转运中",
                },
            ],
        }
        cid, tn, all_tns = _common_pack_tracking_bundle(data)
        self.assertEqual(cid, "HW260501")
        self.assertEqual(tn, "1Z999AA10123456784")
        self.assertEqual(all_tns, ["1Z999AA10123456784", "SUB001", "SUB002"])
        self.assertEqual(
            _common_pack_sub_zycodes(data, outer=tn),
            ["SUB001", "SUB002"],
        )

    def test_outer_zycode_on_result_root(self) -> None:
        data = {"orderno": "O1", "details": []}
        result = {"zycode": "ROOT-TN", "data": data}
        _, tn, all_tns = _common_pack_ids_from_data(data, result=result)
        self.assertEqual(tn, "ROOT-TN")
        self.assertEqual(all_tns, ["ROOT-TN"])

    def test_empty_fields(self) -> None:
        cid, tn, all_tns = _common_pack_ids_from_data({})
        self.assertIsNone(cid)
        self.assertIsNone(tn)
        self.assertIsNone(all_tns)


if __name__ == "__main__":
    unittest.main()
