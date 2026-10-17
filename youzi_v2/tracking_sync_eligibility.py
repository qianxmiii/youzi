"""轨迹同步运单状态范围（内部 / 承运商）。"""

from __future__ import annotations

from youzi_v2.db.shipment_order_status import (
    CARRIER_TRACKING_SYNC_STATUSES,
    INTERNAL_TRACKING_SYNC_STATUSES,
)


def _status_in_sql(codes: frozenset[str], alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    quoted = ", ".join(f"'{c}'" for c in sorted(codes))
    return f"{prefix}status_code IN ({quoted})"


def internal_tracking_sync_eligible_sql(
    alias: str = "",
    *,
    include_delivered: bool = False,
) -> str:
    codes = set(INTERNAL_TRACKING_SYNC_STATUSES)
    if include_delivered:
        codes.add("3")
        codes.add("DELIVERED")
    return _status_in_sql(frozenset(codes), alias)


def carrier_tracking_sync_eligible_sql(
    alias: str = "",
    *,
    include_delivered: bool = False,
) -> str:
    codes = set(CARRIER_TRACKING_SYNC_STATUSES)
    if include_delivered:
        codes.add("3")
        codes.add("DELIVERED")
    return _status_in_sql(frozenset(codes), alias)
