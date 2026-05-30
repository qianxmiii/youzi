"""HWE CMS 轨迹解析单元测试。"""

import json

from youzi_v2.services.carrier_vendors import _fetch_huawell_cms_batch, detect_platform

def test_detect_huawell_cms():
    v = {"apiUrl": "http://47.115.60.246:8000/cms/tracking"}
    assert detect_platform(v) == "huawell_cms"


def test_parse_huawell_cms_batch_structure():
    vendor = {"apiUrl": "http://example/cms/tracking", "uuid": ""}
    payload = [
        {
            "packno": "DPSECO260430142",
            "supcode": "DPSECO260430142",
            "zycode": "1Z999AA10123456784",
            "orderno": "HW260430",
            "details": [
                {
                    "zycode": "SUB-A",
                    "zztm": "2026-05-18 09:20",
                    "guiji": "5-18 已交UPS",
                },
                {"zztm": "2026-05-07 15:04", "guiji": "订单创建"},
            ],
        }
    ]

    class FakeResp:
        status_code = 200
        content = json.dumps(payload).encode("utf-8")

        def raise_for_status(self):
            return None

    import youzi_v2.services.carrier_vendors as mod

    orig = mod.requests.post
    mod.requests.post = lambda *a, **k: FakeResp()
    try:
        out = _fetch_huawell_cms_batch(["DPSECO260430142"], vendor, timeout=1)
    finally:
        mod.requests.post = orig
    logs, err, carrier_id, tracking_number, all_tns = out["DPSECO260430142"]
    assert err is None
    assert carrier_id == "HW260430"
    assert tracking_number == "1Z999AA10123456784"
    assert all_tns == ["1Z999AA10123456784", "SUB-A"]
    assert len(logs) == 2
    assert logs[0].tracking_time == "2026-05-18 09:20:00"
