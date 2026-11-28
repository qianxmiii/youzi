"""提单管理接口。"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..context import _database
from ..services.bills_of_lading import get_bill, list_bills, save_binding

router = APIRouter(prefix="/api/v1/bills-of-lading")


class BillBindingIn(BaseModel):
    voyageId: str | None
    originCallId: str | None = None
    destinationCallId: str | None = None


@router.get("")
def list_bills_of_lading(country: str = "US", search: str = "",
                         state: Literal["", "unbound", "review", "planned", "departed", "arrived", "inspection", "delivered"] = "",
                         limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
                         voyage_id: str | None = None, port_call_id: str | None = None,
                         origin_port: str = "", destination_port: str = "",
                         delivery_scope: Literal["all", "open", "delivered"] = "all"):
    return list_bills(_database, country.strip().upper(), search, state, limit, offset,
                      voyage_id=voyage_id, port_call_id=port_call_id,
                      origin_port=origin_port.strip().upper(), destination_port=destination_port.strip().upper(),
                      delivery_scope=delivery_scope)


@router.get("/detail")
def get_bill_of_lading(bill_no: str):
    bill = get_bill(_database, bill_no.strip().upper())
    if bill is None:
        raise HTTPException(404, "没有该提单的运单")
    return bill


@router.put("/binding")
def bind_bill_of_lading(bill_no: str, body: BillBindingIn):
    bill_no = bill_no.strip().upper()
    try:
        found = save_binding(_database, bill_no, body.voyageId, body.originCallId, body.destinationCallId)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not found:
        raise HTTPException(404, "没有该提单的运单")
    return get_bill_of_lading(bill_no)
