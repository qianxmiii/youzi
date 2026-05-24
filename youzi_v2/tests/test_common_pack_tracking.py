"""鑫鲲鹏 common_pack 报文字段回写。"""

import unittest

from youzi_v2.services.carrier_vendors import _common_pack_ids_from_data


class CommonPackTrackingTest(unittest.TestCase):
    def test_orderno_and_zycode(self) -> None:
        data = {
            "orderno": "ICBU00001036120",
            "zycode": "1Z999AA10123456784",
            "kdzt": "转运中",
            "details": [{"zztm": "2026-05-01 12:00:00", "guiji": "已收货"}],
        }
        cid, tn = _common_pack_ids_from_data(data)
        self.assertEqual(cid, "ICBU00001036120")
        self.assertEqual(tn, "1Z999AA10123456784")

    def test_empty_fields(self) -> None:
        cid, tn = _common_pack_ids_from_data({})
        self.assertIsNone(cid)
        self.assertIsNone(tn)


if __name__ == "__main__":
    unittest.main()
