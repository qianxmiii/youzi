"""内部轨迹仓库占位文案。"""

from youzi_v2.internal_tracking import (
    INTERNAL_WAREHOUSE_PLACEHOLDER,
    is_internal_no_tracking_desc,
    mask_internal_summary,
)
from youzi_v2.services.logistics_tracking import latest_from_logs, logs_from_api_item


def test_is_placeholder():
    assert is_internal_no_tracking_desc(INTERNAL_WAREHOUSE_PLACEHOLDER)
    assert not is_internal_no_tracking_desc("已出库")


def test_mask_summary():
    assert mask_internal_summary("2026-05-18 09:20:00", INTERNAL_WAREHOUSE_PLACEHOLDER) == (
        "",
        "",
    )


def test_latest_from_logs_skips_placeholder():
    logs = latest_from_logs(
        [
            ("2026-05-18 09:20:00", INTERNAL_WAREHOUSE_PLACEHOLDER),
            ("2026-05-16 10:00:00", "已出库"),
        ]
    )
    assert logs == ("2026-05-16 10:00:00", "已出库")


def test_logs_from_api_item_skips_placeholder():
    item = {
        "logisticsInfors": [
            {"nodeTime": "2026-05-18", "nodeDesc": INTERNAL_WAREHOUSE_PLACEHOLDER},
            {"nodeTime": "2026-05-16", "nodeDesc": "已出库"},
        ]
    }
    logs = logs_from_api_item(item)
    assert len(logs) == 1
    assert logs[0][1] == "已出库"
