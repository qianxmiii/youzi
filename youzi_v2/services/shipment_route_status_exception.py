"""按 DPS 关键细状态自动开/关清关类异常。"""

from __future__ import annotations

from typing import Any

from ..db.connection import Database
from ..db.shipment_exception_events_repository import ShipmentExceptionEventsRepository
from ..db.shipment_route_status import (
    CUSTOMS_EXCEPTION_CODES,
    CUSTOMS_EXCEPTION_ROUTE_STATUSES,
    is_milestone_route_status,
)
from ..db.shipments_repository import ShipmentsRepository

_AUTO_NOTE_OPEN = "DPS 细状态自动标记"
_AUTO_NOTE_CLOSE = "DPS 关键节点已离开清关异常"


def apply_customs_exception_from_route_status(
    database: Database,
    shipment_no: str,
    route_status: str | None,
) -> dict[str, Any]:
    """
    - 最新关键节点为 206/402 → 开启对应清关异常（不覆盖掉件/暂扣等非清关异常）
    - 最新关键节点为其他关键节点 → 仅当当前异常为清关类时自动解除
    - 无细状态 / 非关键节点 → 不动
    """
    sn = (shipment_no or "").strip()
    rs = (route_status or "").strip().upper()
    if not sn:
        return {"action": "noop", "reason": "empty_shipment_no"}

    ship = ShipmentsRepository(database).get_by_shipment_no(sn)
    if ship is None:
        return {"action": "noop", "reason": "not_found"}

    current = (ship.get("exceptionCode") or "").strip().upper()
    exc_repo = ShipmentExceptionEventsRepository(database)

    if rs in CUSTOMS_EXCEPTION_ROUTE_STATUSES:
        if current == rs:
            return {"action": "skip", "reason": "already_open", "exceptionCode": rs}
        if current and current not in CUSTOMS_EXCEPTION_CODES:
            return {
                "action": "skip",
                "reason": "manual_exception_present",
                "exceptionCode": current,
            }
        result = exc_repo.open_for_shipment_nos(
            [sn],
            rs,
            note=_AUTO_NOTE_OPEN,
        )
        return {
            "action": "opened" if result.get("opened") else "skip",
            "exceptionCode": rs,
            "detail": result,
        }

    if rs and is_milestone_route_status(rs):
        if current not in CUSTOMS_EXCEPTION_CODES:
            return {"action": "noop", "reason": "not_customs_exception"}
        result = exc_repo.close_for_shipment_nos(
            [sn],
            note=_AUTO_NOTE_CLOSE,
        )
        return {
            "action": "closed" if result.get("closed") else "skip",
            "previousExceptionCode": current,
            "routeStatus": rs,
            "detail": result,
        }

    return {"action": "noop", "reason": "no_milestone_route_status"}
