"""HWE CMS 轨迹解析单元测试。"""

from youzi_v2.services.carrier_vendors import _fetch_huawell_cms_batch, detect_platform


def test_detect_huawell_cms():
    v = {"apiUrl": "http://47.115.60.246:8000/cms/tracking"}
    assert detect_platform(v) == "huawell_cms"


def test_parse_huawell_cms_batch_structure():
    vendor = {"apiUrl": "http://example/cms/tracking", "uuid": ""}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return [
                {
                    "packno": "DPSECO260430142",
                    "supcode": "DPSECO260430142",
                    "details": [
                        {"zztm": "2026-05-18 09:20", "guiji": "5-18 已交UPS"},
                        {"zztm": "2026-05-07 15:04", "guiji": "订单创建"},
                    ],
                }
            ]

    import youzi_v2.services.carrier_vendors as mod

    orig = mod.requests.post
    mod.requests.post = lambda *a, **k: FakeResp()
    try:
        out = _fetch_huawell_cms_batch(["DPSECO260430142"], vendor, timeout=1)
    finally:
        mod.requests.post = orig
    logs, err, carrier_id, tracking_number = out["DPSECO260430142"]
    assert err is None
    assert carrier_id is None
    assert tracking_number is None
    assert len(logs) == 2
    assert logs[0][0] == "2026-05-18 09:20:00"
