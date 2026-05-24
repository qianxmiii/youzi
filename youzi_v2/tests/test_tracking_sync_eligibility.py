"""轨迹同步状态范围。"""

from tracking_sync_eligibility import (
    CARRIER_TRACKING_SYNC_STATUS_CODES,
    INTERNAL_TRACKING_SYNC_STATUS_CODES,
    carrier_tracking_sync_eligible_sql,
    internal_tracking_sync_eligible_sql,
)


def test_internal_statuses_include_unknown():
    assert "UNKNOWN" in INTERNAL_TRACKING_SYNC_STATUS_CODES
    assert "DELIVERED" not in INTERNAL_TRACKING_SYNC_STATUS_CODES


def test_carrier_statuses_in_transit_only():
    assert CARRIER_TRACKING_SYNC_STATUS_CODES == frozenset({"IN_TRANSIT"})


def test_internal_sql():
    sql = internal_tracking_sync_eligible_sql()
    assert "UNKNOWN" in sql
    assert "IN_TRANSIT" in sql
    assert "DELIVERED" not in sql


def test_carrier_sql():
    assert carrier_tracking_sync_eligible_sql() == "status_code IN ('IN_TRANSIT')"
