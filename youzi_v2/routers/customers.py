from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response

from ..context import *
from ..services.customer_excel import build_customer_export_bytes
from ..services.payment_reminder_rules import SETTLEMENT_MONTHLY

router = APIRouter()

_CUSTOMER_EXPORT_MAX = 10_000

@router.get("/api/v1/customers")
def list_customers(
    search: str | None = None,
    vip_only: bool | None = Query(None, alias="vipOnly"),
    limit: int = 200,
    offset: int = 0,
):
    return customers_repo.list_rows(
        search=search, vip_only=vip_only, limit=limit, offset=offset
    )

@router.get("/api/v1/customers/export")
def export_customers_excel(
    search: str | None = None,
    vip_only: bool | None = Query(None, alias="vipOnly"),
    limit: int = Query(_CUSTOMER_EXPORT_MAX, le=_CUSTOMER_EXPORT_MAX),
    offset: int = 0,
):
    """导出客户列表（Excel；筛选条件与列表一致）。"""
    result = customers_repo.list_rows(
        search=search,
        vip_only=vip_only,
        limit=limit,
        offset=offset,
    )
    total = int(result.get("total") or 0)
    if total > _CUSTOMER_EXPORT_MAX:
        raise HTTPException(
            status_code=400,
            detail=(
                f"当前筛选共 {total} 条，超过导出上限 {_CUSTOMER_EXPORT_MAX}，请缩小筛选范围"
            ),
        )
    data = build_customer_export_bytes(result.get("items") or [])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"客户导出_{ts}.xlsx"
    encoded = quote(filename)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.post("/api/v1/customers/sync-from-shipments", response_model=CustomerSyncResult)
def sync_customers_from_shipments():
    """从运单表抓取全部去重客户名写入客户表（已存在的不覆盖 VIP 状态）。"""
    return CustomerSyncResult(**customers_repo.sync_from_shipments())

@router.post("/api/v1/customers", status_code=201)
def create_customer(body: CustomerIn):
    try:
        return customers_repo.create(
            body.customer_name,
            note=body.note,
            is_vip=body.is_vip,
            customer_lang=body.customer_lang,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.patch("/api/v1/customers/{item_id}")
def update_customer(item_id: str, body: CustomerUpdateIn):
    try:
        if body.customer_name is not None:
            row = customers_repo.rename(
                item_id,
                body.customer_name,
                update_shipments=bool(body.update_shipments),
            )
        else:
            row = customers_repo.patch(
                item_id,
                is_vip=body.is_vip,
                note=body.note,
                customer_lang=body.customer_lang,
                settlement_method=body.settlement_method,
                settlement_day=body.settlement_day,
                clear_settlement_day=body.settlement_method is not None
                and body.settlement_method != SETTLEMENT_MONTHLY
                and body.settlement_day is None,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return row

@router.delete("/api/v1/customers/{item_id}", status_code=204)
def delete_customer(item_id: str):
    if not customers_repo.delete(item_id):
        raise HTTPException(status_code=404, detail="客户不存在")
    return Response(status_code=204)
