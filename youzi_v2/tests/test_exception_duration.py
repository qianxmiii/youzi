"""异常持续时间展示测试。"""

from youzi_v2.db.exception_duration import format_duration


def test_format_duration_days_only() -> None:
    assert format_duration(3 * 86400, opened_time="2026-01-01 10:00:00", closed_time="2026-01-04 10:00:00") == "3天"


def test_format_duration_months_and_days() -> None:
    assert (
        format_duration(None, opened_time="2026-01-15 08:00:00", closed_time="2026-03-20 08:00:00")
        == "2月5天"
    )


def test_format_duration_months_only() -> None:
    assert (
        format_duration(None, opened_time="2026-01-01 00:00:00", closed_time="2026-03-01 00:00:00")
        == "2月"
    )


def test_format_duration_less_than_one_day() -> None:
    assert format_duration(3600, opened_time="2026-01-01 10:00:00", closed_time="2026-01-01 11:00:00") == "不足1天"
