from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ..context import *
from ..schemas.payment_reminders import (
    PaymentCollectionTermIn,
    PaymentReminderFollowupBatchIn,
    PaymentReminderFollowupBatchResult,
    PaymentReminderFollowupIn,
)
from ..services.payment_reminder_excel import build_payment_reminder_export_bytes

router = APIRouter()

_EXPORT_MAX = 10_000


@router.get("/api/v1/shipments/payment-reminders/summary")
def payment_reminder_summary(
    fcl_only: bool | None = Query(False, alias="fclOnly"),
):
    """待催 / 全部未付款数量（侧栏角标与页面标题统计）。默认排除整柜。"""
    return shipment_payment_followups_repo.reminder_summary(fcl_only=fcl_only)


@router.get("/api/v1/shipments/payment-reminders/customer-ranking")
def payment_reminder_customer_ranking(
    scope: str = Query("todo"),
    settlement_method: str | None = Query(None, alias="settlementMethod"),
    reminder_type: str | None = Query(None, alias="reminderType"),
    followup_status: str | None = Query(None, alias="followupStatus"),
    search: str | None = None,
    fcl_only: bool | None = Query(False, alias="fclOnly"),
    min_receivable: float | None = Query(None, alias="minReceivable"),
    receivable_pending: bool = Query(False, alias="receivablePending"),
    channel_category: str | None = Query(None, alias="channelCategory"),
    limit: int = Query(10, ge=1, le=100),
):
    """按客户汇总当前筛选下大于 0 的应收。不按客户收窄，便于点排名后列表筛选。"""
    return shipment_payment_followups_repo.customer_ranking(
        scope=scope,
        settlement_method=settlement_method,
        reminder_type=reminder_type,
        followup_status=followup_status,
        search=search,
        fcl_only=fcl_only,
        min_receivable=min_receivable,
        receivable_pending=receivable_pending,
        channel_category=channel_category,
        limit=limit,
    )


@router.get("/api/v1/shipments/payment-reminders/export")
def export_payment_reminders_excel(
    scope: str = Query("todo"),
    customer: str | None = None,
    settlement_method: str | None = Query(None, alias="settlementMethod"),
    reminder_type: str | None = Query(None, alias="reminderType"),
    followup_status: str | None = Query(None, alias="followupStatus"),
    search: str | None = None,
    fcl_only: bool | None = Query(False, alias="fclOnly"),
    min_receivable: float | None = Query(None, alias="minReceivable"),
    receivable_pending: bool = Query(False, alias="receivablePending"),
    sort_by: str | None = Query(None, alias="sortBy"),
    channel_category: str | None = Query(None, alias="channelCategory"),
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
        fcl_only=fcl_only,
        min_receivable=min_receivable,
        receivable_pending=receivable_pending,
        sort_by=sort_by,
        channel_category=channel_category,
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
    fcl_only: bool | None = Query(False, alias="fclOnly"),
    min_receivable: float | None = Query(None, alias="minReceivable"),
    receivable_pending: bool = Query(False, alias="receivablePending"),
    sort_by: str | None = Query(None, alias="sortBy"),
    channel_category: str | None = Query(None, alias="channelCategory"),
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
        fcl_only=fcl_only,
        min_receivable=min_receivable,
        receivable_pending=receivable_pending,
        sort_by=sort_by,
        channel_category=channel_category,
        limit=limit,
        offset=offset,
    )


@router.post("/api/v1/shipments/payment-reminders/collection-term")
def set_payment_collection_term(body: PaymentCollectionTermIn):
    """给选中运单设置收款起算日。应付款日 = 起算日 + 账期，默认 21 天。"""
    ids = [item.strip() for item in body.shipment_ids if item and item.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="请选择运单")
    try:
        return shipment_payment_followups_repo.set_collection_terms(
            ids,
            start_date=body.collection_start_date,
            term_days=body.payment_term_days,
            advance_days=body.reminder_advance_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
