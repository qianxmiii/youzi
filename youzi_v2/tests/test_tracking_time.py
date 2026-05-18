"""轨迹时间规范化。"""

from youzi_v2.db.datetime_util import normalize_tracking_time


def test_pad_minutes_without_seconds():
    assert normalize_tracking_time("2026-05-18 09:20") == "2026-05-18 09:20:00"


def test_keep_seconds():
    assert normalize_tracking_time("2026-05-18 09:20:31") == "2026-05-18 09:20:31"


def test_date_only():
    assert normalize_tracking_time("2026-05-18") == "2026-05-18 00:00:00"
