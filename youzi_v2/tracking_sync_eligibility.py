"""轨迹同步运单状态范围（内部 / 承运商）。"""

from __future__ import annotations

# 内部轨迹：导入默认为 UNKNOWN，同步后由 API 回写状态；已签收不再拉取
INTERNAL_TRACKING_SYNC_STATUS_CODES: frozenset[str] = frozenset(
    {"IN_TRANSIT", "UNKNOWN", "INSPECTION"}
)

# 承运商轨迹：仅转运中仍在途
CARRIER_TRACKING_SYNC_STATUS_CODES: frozenset[str] = frozenset({"IN_TRANSIT"})


def _status_in_sql(codes: frozenset[str], alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    quoted = ", ".join(f"'{c}'" for c in sorted(codes))
    return f"{prefix}status_code IN ({quoted})"


def internal_tracking_sync_eligible_sql(
    alias: str = "",
    *,
    include_delivered: bool = False,
) -> str:
    codes = INTERNAL_TRACKING_SYNC_STATUS_CODES
    if include_delivered:
        codes = codes | frozenset({"DELIVERED"})
    return _status_in_sql(codes, alias)


def carrier_tracking_sync_eligible_sql(
    alias: str = "",
    *,
    include_delivered: bool = False,
) -> str:
    codes = CARRIER_TRACKING_SYNC_STATUS_CODES
    if include_delivered:
        codes = codes | frozenset({"DELIVERED"})
    return _status_in_sql(codes, alias)
