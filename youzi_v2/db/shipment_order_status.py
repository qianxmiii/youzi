"""DPS 运单 Status（0/01/1/2/3/4）与港前/在途工作台划分。"""

from __future__ import annotations

from typing import Any

# DPS Status
STATUS_ORDERED = "0"
STATUS_PICKED_UP = "01"
STATUS_WAREHOUSE_IN = "1"
STATUS_IN_TRANSIT = "2"
STATUS_DELIVERED = "3"
STATUS_CANCELLED = "4"

# 迁移前本地粗状态
LEGACY_IN_TRANSIT = "IN_TRANSIT"
LEGACY_DELIVERED = "DELIVERED"
LEGACY_UNKNOWN = "UNKNOWN"
LEGACY_INSPECTION = "INSPECTION"

PRE_PORT_STATUSES: frozenset[str] = frozenset(
    {STATUS_ORDERED, STATUS_PICKED_UP, STATUS_WAREHOUSE_IN, STATUS_CANCELLED}
)

TRANSIT_WORKSPACE_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_IN_TRANSIT,
        STATUS_DELIVERED,
        LEGACY_IN_TRANSIT,
        LEGACY_DELIVERED,
    }
)

# 列表 statusCode 筛选：DPS 与迁移前粗码互通
_STATUS_FILTER_VARIANTS: dict[str, frozenset[str]] = {
    STATUS_IN_TRANSIT: frozenset({STATUS_IN_TRANSIT, LEGACY_IN_TRANSIT}),
    LEGACY_IN_TRANSIT: frozenset({STATUS_IN_TRANSIT, LEGACY_IN_TRANSIT}),
    STATUS_DELIVERED: frozenset({STATUS_DELIVERED, LEGACY_DELIVERED}),
    LEGACY_DELIVERED: frozenset({STATUS_DELIVERED, LEGACY_DELIVERED}),
}

INTERNAL_TRACKING_SYNC_STATUSES: frozenset[str] = frozenset(
    {STATUS_IN_TRANSIT, LEGACY_IN_TRANSIT, LEGACY_INSPECTION, LEGACY_UNKNOWN}
)

CARRIER_TRACKING_SYNC_STATUSES: frozenset[str] = frozenset(
    {STATUS_IN_TRANSIT, LEGACY_IN_TRANSIT}
)

DELIVERED_STATUSES: frozenset[str] = frozenset(
    {STATUS_DELIVERED, LEGACY_DELIVERED}
)

WORKSPACE_PREPORT = "preport"
WORKSPACE_TRANSIT = "transit"
VALID_WORKSPACES: frozenset[str] = frozenset({WORKSPACE_PREPORT, WORKSPACE_TRANSIT})


def normalize_dps_order_status(value: Any) -> str | None:
    """解析 DPS 行字段 status（保留 01）。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text in PRE_PORT_STATUSES | {STATUS_IN_TRANSIT, STATUS_DELIVERED, STATUS_CANCELLED}:
        return text
    if text == "01":
        return STATUS_PICKED_UP
    try:
        n = int(float(text))
    except (TypeError, ValueError):
        return None
    mapping = {
        0: STATUS_ORDERED,
        1: STATUS_WAREHOUSE_IN,
        2: STATUS_IN_TRANSIT,
        3: STATUS_DELIVERED,
        4: STATUS_CANCELLED,
    }
    return mapping.get(n)


def validate_workspace(value: str | None) -> str | None:
    key = (value or "").strip().lower()
    if not key:
        return None
    if key not in VALID_WORKSPACES:
        raise ValueError("workspace 须为 preport 或 transit")
    return key


def _status_in_sql(codes: frozenset[str], alias: str = "s") -> tuple[str, list[Any]]:
    prefix = f"{alias}." if alias else ""
    ordered = sorted(codes)
    placeholders = ", ".join("?" for _ in ordered)
    return (
        f"TRIM(COALESCE({prefix}status_code, '')) IN ({placeholders})",
        list(ordered),
    )


def status_code_filter_sql(
    status_code: str,
    *,
    alias: str = "s",
) -> tuple[str, list[Any]]:
    """单状态筛选（含 IN_TRANSIT↔2、DELIVERED↔3）。"""
    raw = (status_code or "").strip()
    if not raw:
        return "", []
    key = raw.upper()
    variants = _STATUS_FILTER_VARIANTS.get(raw) or _STATUS_FILTER_VARIANTS.get(key)
    prefix = f"{alias}." if alias else ""
    col = f"TRIM(COALESCE({prefix}status_code, ''))"
    if variants:
        ordered = sorted(variants)
        placeholders = ", ".join("?" for _ in ordered)
        return f"{col} IN ({placeholders})", list(ordered)
    return f"{col} = ?", [raw]


def migrate_legacy_shipment_status_codes(conn) -> None:
    """一次性兼容：粗码 IN_TRANSIT/DELIVERED → DPS 2/3。"""
    conn.execute(
        """
        UPDATE shipments
        SET status_code = '2'
        WHERE UPPER(TRIM(COALESCE(status_code, ''))) = 'IN_TRANSIT'
        """
    )
    conn.execute(
        """
        UPDATE shipments
        SET status_code = '3'
        WHERE UPPER(TRIM(COALESCE(status_code, ''))) = 'DELIVERED'
        """
    )


def workspace_status_filter_sql(
    workspace: str | None,
    *,
    alias: str = "s",
) -> tuple[str, list[Any]]:
    """未指定 status_code 时，按工作台限制可见范围。"""
    ws = validate_workspace(workspace)
    if ws == WORKSPACE_PREPORT:
        return _status_in_sql(PRE_PORT_STATUSES, alias)
    if ws == WORKSPACE_TRANSIT:
        return _status_in_sql(TRANSIT_WORKSPACE_STATUSES, alias)
    return "", []


def is_delivered_status_code(code: str | None) -> bool:
    key = (code or "").strip().upper()
    return key in DELIVERED_STATUSES or key == LEGACY_DELIVERED
