"""腾信 TXFBA getOrderTrackList 单元测试。"""

from youzi_v2.services.carrier_vendors import (
    _fetch_txfba_track_by_bill_no,
    detect_platform,
    fetch_txfba_batch_for_rows,
    parse_txfba_track_list,
)

SAMPLE_TRACKS = [
    {
        "billNo": "ICBU00001077014",
        "customerBillNo": "DPSECO260512110",
        "trackTime": "2026-05-18 09:39:54",
        "trackInfo": "货物已完成操作并送往航司",
    },
    {
        "billNo": "ICBU00001077014",
        "customerBillNo": "DPSECO260512110",
        "trackTime": "2026-05-16 15:16:02",
        "trackInfo": "客户已下单提交预报，请客服人员跟进服务",
    },
]


def test_detect_txfba_platform():
    v = {
        "apiUrl": "https://interface.txfba.com/bussOrderTrack/getOrderTrackList",
        "platform": "txfba",
    }
    assert detect_platform(v) == "txfba"


def test_parse_txfba_track_list_newest_first():
    logs = parse_txfba_track_list(SAMPLE_TRACKS)
    assert len(logs) == 2
    assert logs[0][0] == "2026-05-18 09:39:54"
    assert "航司" in logs[0][1]


def test_fetch_txfba_batch_for_rows_requires_carrier_id():
    vendor = {"apiUrl": "https://interface.txfba.com/bussOrderTrack/getOrderTrackList"}
    out = fetch_txfba_batch_for_rows(
        [{"shipment_no": "DPSECO260512110", "carrier_id": ""}],
        vendor,
        timeout=1,
    )
    _, err, _, _ = out["DPSECO260512110"]
    assert err and "carrier_id" in err


def test_fetch_txfba_track_by_bill_no():
    vendor = {
        "apiUrl": "https://interface.txfba.com/bussOrderTrack/getOrderTrackList",
        "token": "test",
    }

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 200, "message": "成功", "data": SAMPLE_TRACKS, "total": 2}

    import youzi_v2.services.carrier_vendors as mod

    orig = mod.requests.post
    mod.requests.post = lambda *a, **k: FakeResp()
    try:
        logs, err, carrier_id, tn = _fetch_txfba_track_by_bill_no(
            "ICBU00001077014", vendor, timeout=1
        )
        out = fetch_txfba_batch_for_rows(
            [{"shipment_no": "DPSECO260512110", "carrier_id": "ICBU00001077014"}],
            vendor,
            timeout=1,
        )
    finally:
        mod.requests.post = orig

    assert err is None
    assert carrier_id is None
    assert len(logs) == 2
    logs2, err2, _, _ = out["DPSECO260512110"]
    assert err2 is None
    assert len(logs2) == 2
