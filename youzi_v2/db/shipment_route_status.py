"""DPS 轨迹细状态：commerceWaybillRouteInfo.status → 本地 route_status。"""

from __future__ import annotations

from typing import Any

# (local_code, dps_status, name_zh, name_en, sort_order, is_milestone)
# is_milestone=False：非关键节点（如信息传递），不同步写入 route_status、列表不展示
ROUTE_STATUS_SEEDS: list[tuple[str, str, str, str, int, bool]] = [
    ("INFO", "100", "信息传递", "Info", 10, False),
    ("WAREHOUSE_IN", "202", "入库", "Warehouse in", 20, True),
    ("EXPORT_CUSTOMS_RELEASE", "205", "出口海关放行", "Export customs release", 30, True),
    ("EXPORT_CUSTOMS_EXCEPTION", "206", "出口海关异常", "Export customs exception", 40, True),
    ("DEPARTED_POL", "301", "离开起运港", "Departed POL", 50, True),
    ("ARRIVED_POD", "306", "到达目的港", "Arrived POD", 60, True),
    ("IMPORT_CUSTOMS_EXCEPTION", "402", "进口清关异常", "Import customs exception", 70, True),
    ("DEST_TRANSIT_WAREHOUSE", "502", "到达目的国中转仓库", "Dest transit warehouse", 80, True),
    ("LAST_MILE_HANDOVER", "510", "快递派-已交仓", "Last-mile handover", 90, True),
    ("TRACK_SIGNED", "601", "轨迹签收", "Track signed", 100, True),
]

_NON_MILESTONE_CODES: frozenset[str] = frozenset(
    code for code, *_rest, is_milestone in ROUTE_STATUS_SEEDS if not is_milestone
)
_DPS_TO_CODE: dict[str, str] = {dps: code for code, dps, *_ in ROUTE_STATUS_SEEDS}
_CODE_TO_LABEL: dict[str, str] = {code: zh for code, _dps, zh, *_ in ROUTE_STATUS_SEEDS}

# 细状态 → 自动异常码（与 shipment_exception_codes 一致）
CUSTOMS_EXCEPTION_ROUTE_STATUSES: frozenset[str] = frozenset(
    {
        "EXPORT_CUSTOMS_EXCEPTION",
        "IMPORT_CUSTOMS_EXCEPTION",
    }
)
CUSTOMS_EXCEPTION_CODES: frozenset[str] = CUSTOMS_EXCEPTION_ROUTE_STATUSES


def normalize_dps_route_status(raw: Any) -> str | None:
    text = str(raw).strip() if raw is not None else ""
    if not text:
        return None
    # 允许 "601" / 601 / "601.0"
    try:
        text = str(int(float(text)))
    except (TypeError, ValueError):
        pass
    return text or None


def is_milestone_route_status(code: str | None) -> bool:
    key = (code or "").strip().upper()
    if not key:
        return False
    return key not in _NON_MILESTONE_CODES and key in _CODE_TO_LABEL


def map_dps_route_status(raw: Any) -> str | None:
    """
    DPS status → 本地 route_status。
    非关键节点（如 100 信息传递）返回 None，避免写入/覆盖关键细状态。
    """
    dps = normalize_dps_route_status(raw)
    if not dps:
        return None
    code = _DPS_TO_CODE.get(dps)
    if not code or code in _NON_MILESTONE_CODES:
        return None
    return code


def route_status_label(code: str | None) -> str:
    key = (code or "").strip().upper()
    if not key:
        return ""
    return _CODE_TO_LABEL.get(key, key)


def list_route_status_options(*, milestones_only: bool = True) -> list[dict[str, str]]:
    return [
        {"code": code, "dpsStatus": dps, "nameZh": zh, "nameEn": en}
        for code, dps, zh, en, _order, is_milestone in ROUTE_STATUS_SEEDS
        if (is_milestone if milestones_only else True)
    ]
