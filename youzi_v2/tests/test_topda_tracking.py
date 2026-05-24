"""Topda轨迹解析单元测试（不依赖外网）。"""

from youzi_v2.services.carrier_vendors import (
    _extract_carrier_id,
    parse_topda_item,
    parse_topda_tracking_bundle,
)


SAMPLE_ITEM = {
    "trackingNum": "DPSECO260513125",
    "poNum": "DPSECO260513125",
    "notFound": None,
    "trackings": [
        {
            "time": "2026-05-16 16:29",
            "context": "已揽收完成",
            "node": "wmsIn",
        },
        {
            "time": "2026-05-18 16:12",
            "context": "已装柜配载，ETD:2026/05/21,ETA:2026/06/04,船名航次：CSCL BOHAI SEA/076E",
        },
    ],
    "headNodes": [
        {"time": "2026-05-15", "node": "Booked", "context": None},
        {"time": "2026-05-16", "node": "pickup", "context": None},
    ],
}


def test_parse_topda_item_sorts_newest_first():
    logs = parse_topda_item(SAMPLE_ITEM)
    assert len(logs) >= 4
    assert logs[0].tracking_time == "2026-05-18 16:12:00"
    assert "装柜" in logs[0].tracking_desc


def test_parse_topda_head_node_labels():
    logs = parse_topda_item(SAMPLE_ITEM)
    texts = [e.tracking_desc for e in logs]
    assert any("已订舱" in t for t in texts)
    assert any("已提货" in t for t in texts)


def test_extract_carrier_id_job_num():
    assert _extract_carrier_id({**SAMPLE_ITEM, "jobNum": "JOB-888"}) == "JOB-888"


def test_parse_topda_tracking_bundle_main_and_subs():
    item = {
        "trackingNum": "DPSECO260410140",
        "jobNum": "TPD260404860",
        "poNum": "DPSECO260410140",
        "subTrackings": [
            {"trackingNum": "870833728471"},
            {"trackingNum": "870833728482"},
        ],
    }
    job, main, all_nums = parse_topda_tracking_bundle(item)
    assert job == "TPD260404860"
    assert main == "870833728471"
    assert all_nums == ["870833728471", "870833728482"]
    assert "DPSECO260410140" not in all_nums


SAME_MINUTE_TRACKINGS = {
    "trackingNum": "DPSECO260417030",
    "trackings": [
        {
            "id": 26917259,
            "time": "2026-05-22 09:56",
            "eventTime": "2026-05-22T09:56:26+08:00",
            "context": "您的订单2026-05-22 到港，等待卸船中，如有更新会及时再通知",
            "node": "arrivedPod",
        },
        {
            "id": 26917295,
            "time": "2026-05-22 09:56",
            "eventTime": "2026-05-22T09:56:40+08:00",
            "context": "您的订单2026-05-22 已卸船，提柜时间待确认中",
            "node": "已卸船",
        },
    ],
    "headNodes": [
        {"time": "2026-05-22", "node": "arrivedPod", "context": None},
    ],
}


def test_parse_topda_same_minute_uses_event_time_order():
    logs = parse_topda_item(SAME_MINUTE_TRACKINGS)
    assert logs[0].tracking_time == "2026-05-22 09:56:40"
    assert "已卸船" in logs[0].tracking_desc
    assert logs[0].vendor_event_id == "topda:26917295"
    assert logs[1].tracking_time == "2026-05-22 09:56:26"
    assert "到港" in logs[1].tracking_desc
    assert logs[1].vendor_event_id == "topda:26917259"
    assert not any(
        e.tracking_time == "2026-05-22 00:00:00" and "已到港" in e.tracking_desc for e in logs
    )
