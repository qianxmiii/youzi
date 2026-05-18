"""内部路由轨迹占位文案（视为无有效轨迹）。"""

from __future__ import annotations

INTERNAL_WAREHOUSE_PLACEHOLDER = "Your goods are in the warehouse"


def is_internal_no_tracking_desc(desc: str | None) -> bool:
    return (desc or "").strip() == INTERNAL_WAREHOUSE_PLACEHOLDER


def mask_internal_summary(time: str | None, desc: str | None) -> tuple[str, str]:
    if is_internal_no_tracking_desc(desc):
        return "", ""
    return (time or "").strip(), (desc or "").strip()
