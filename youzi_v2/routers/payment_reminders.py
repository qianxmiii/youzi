from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ..context import *
from ..schemas.payment_reminders import (
    PaymentReminderFollowupBatchIn,
    PaymentReminderFollowupBatchResult,
    PaymentReminderFollowupIn,
)
from ..services.payment_reminder_excel import build_payment_reminder_export_bytes

router = APIRouter()

_EXPORT_MAX = 10_000


@router.get("/api/v1/shipments/payment-reminders/summary")
def payment_reminder_summary():
    """待催 / 全部未付款数量（侧栏角标与页面标题统计）。"""
    return shipment_payment_followups_repo.reminder_summary()


@router.get("/api/v1/shipments/payment-reminders/export")
def export_payment_reminders_excel(
    scope: str = Query("todo"),
    customer: str | None = None,
    settlement_method: str | None = Query(None, alias="settlementMethod"),
    reminder_type: str | None = Query(None, alias="reminderType"),
    followup_status: str | None = Query(None, alias="followupStatus"),
    search: str | None = None,
    limit: int = Query(_EXPORT_MAX, le=_EXPORT_MAX),
    offset: int = 0,
):
    """导出当前筛选条件下的催款列表（Excel）。"""
    result = shipment_payment_followups_repo.list_reminders(
        scope=scope,
        customer=customer,
        settlement_method=settlement_method,
        reminder_type=reminder_type,
        followup_status=followup_status,
        search=search,
        limit=limit,
        offset=offset,
    )
    total = int(result.get("total") or 0)
    if total > _EXPORT_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"当前筛选共 {total} 条，超过导出上限 {_EXPORT_MAX}，请缩小筛选范围",
        )
    data = build_payment_reminder_export_bytes(result.get("items") or [])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"催款列表导出_{ts}.xlsx"
    encoded = quote(filename)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get("/api/v1/shipments/payment-reminders")
def list_payment_reminders(
    scope: str = Query("todo"),
    customer: str | None = None,
    settlement_method: str | None = Query(None, alias="settlementMethod"),
    reminder_type: str | None = Query(None, alias="reminderType"),
    followup_status: str | None = Query(None, alias="followupStatus"),
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    return shipment_payment_followups_repo.list_reminders(
        scope=scope,
        customer=customer,
        settlement_method=settlement_method,
        reminder_type=reminder_type,
        followup_status=followup_status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/api/v1/shipments/payment-reminders/{shipment_id}/followups")
def list_payment_reminder_followups(shipment_id: str):
    row = shipments_repo.get_by_id(shipment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="运单不存在")
    return {"items": shipment_payment_followups_repo.list_followups(shipment_id)}


@router.post("/api/v1/shipments/payment-reminders/{shipment_id}/followups")
def create_payment_reminder_followup(shipment_id: str, body: PaymentReminderFollowupIn):
    try:
        return shipment_payment_followups_repo.create_followup(
            shipment_id,
            note=body.note,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="运单不存在") from None


@router.post(
    "/api/v1/shipments/payment-reminders/followups/batch",
    response_model=PaymentReminderFollowupBatchResult,
)
def batch_create_payment_reminder_followups(body: PaymentReminderFollowupBatchIn):
    ids = [i.strip() for i in body.shipment_ids if i and i.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="shipmentIds 不能为空")
    result = shipment_payment_followups_repo.batch_create_followups(ids, note=body.note)
    return PaymentReminderFollowupBatchResult(**result)
