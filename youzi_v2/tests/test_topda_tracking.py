"""拓普达轨迹解析单元测试（不依赖外网）。"""

from youzi_v2.services.carrier_vendors import _extract_carrier_id, parse_topda_item


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
    assert logs[0][0] == "2026-05-18 16:12"
    assert "装柜" in logs[0][1]


def test_parse_topda_head_node_labels():
    logs = parse_topda_item(SAMPLE_ITEM)
    texts = [d for _, d in logs]
    assert any("已订舱" in t for t in texts)
    assert any("已提货" in t for t in texts)


def test_extract_carrier_id_job_num():
    assert _extract_carrier_id({**SAMPLE_ITEM, "jobNum": "JOB-888"}) == "JOB-888"
