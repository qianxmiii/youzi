"""订单流转：独立提醒，不读写运单表。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ..context import LOGISTICS_CONFIG_PATH, _database
from ..db.order_flow_repository import OrderFlowRepository
from ..services.order_flow_settings import (
    get_order_flow_list_seen_at,
    get_order_flow_poll_settings,
    get_order_flow_reminder_seen_at,
    mark_order_flow_list_seen,
    mark_order_flow_reminders_seen,
    save_order_flow_poll_enabled,
)
from ..services.order_flow_sync import run_order_flow_sync

router = APIRouter(tags=["order-flow"])
_repo = OrderFlowRepository(_database)


class OrderFlowSettingsUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    enabled: bool = Field(alias="enabled")


def _seen_at() -> str:
    return get_order_flow_reminder_seen_at(_database)


@router.get("/api/v1/order-flow/summary")
def order_flow_summary():
    data = _repo.summary(_seen_at())
    data.update(get_order_flow_poll_settings(_database).to_api_dict())
    data["listSeenAt"] = get_order_flow_list_seen_at(_database)
    return data


@router.get("/api/v1/order-flow/nodes")
def order_flow_nodes():
    seen_at = _seen_at()
    summary = _repo.summary(seen_at)
    return {"unseenCount": summary["unseenCount"], "nodes": _repo.node_counts(seen_at)}


@router.post("/api/v1/order-flow/reminders/seen")
def order_flow_mark_seen():
    mark_order_flow_reminders_seen(_database)
    data = _repo.summary(_seen_at())
    data.update(get_order_flow_poll_settings(_database).to_api_dict())
    return data


@router.post("/api/v1/order-flow/list-seen")
def order_flow_mark_list_seen():
    seen_at = mark_order_flow_list_seen(_database)
    return {"listSeenAt": seen_at}


@router.get("/api/v1/order-flow/statuses")
def order_flow_statuses():
    return {"items": _repo.list_statuses()}


@router.get("/api/v1/order-flow/customers")
def order_flow_customers():
    return {"items": _repo.list_customers()}


@router.get("/api/v1/order-flow/warehouses")
def order_flow_warehouses():
    return {"items": _repo.list_warehouses()}


@router.get("/api/v1/order-flow/countries")
def order_flow_countries():
    return {"items": _repo.list_countries()}


@router.get("/api/v1/order-flow/channels")
def order_flow_channels():
    return {"items": _repo.list_channels()}


@router.get("/api/v1/order-flow/{waybill_no}/logs")
def order_flow_logs(waybill_no: str):
    try:
        return {"items": _repo.status_logs(waybill_no)}
    except KeyError:
        raise HTTPException(status_code=404, detail="订单不存在") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/order-flow")
def list_order_flow(
    scope: str = Query("active"),
    search: str = Query(""),
    status: str = Query(""),
    customer: str = Query(""),
    warehouse: str = Query(""),
    country: str = Query(""),
    channel: list[str] = Query(default=[]),
):
    if scope not in {"active", "mine", "ended", "all", "remind"}:
        raise HTTPException(status_code=400, detail="scope 无效")
    items = _repo.list_rows(
        scope=scope,
        search=search,
        status=status,
        customer=customer,
        warehouse=warehouse,
        country=country,
        channel=",".join(
            part.strip()
            for item in channel
            for part in str(item).split(",")
            if part.strip()
        ),
    )
    return {"items": items, "total": len(items), **_repo.summary(_seen_at())}


@router.post("/api/v1/order-flow/refresh")
def refresh_order_flow():
    try:
        result = run_order_flow_sync(_database, LOGISTICS_CONFIG_PATH, force=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**result, **_repo.summary(_seen_at())}


@router.put("/api/v1/order-flow/settings")
def update_order_flow_settings(body: OrderFlowSettingsUpdate):
    settings = save_order_flow_poll_enabled(_database, enabled=body.enabled)
    return settings.to_api_dict()

