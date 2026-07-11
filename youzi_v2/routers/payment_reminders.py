from fastapi import APIRouter, HTTPException, Query

from ..context import *
from ..schemas.payment_reminders import (
    PaymentReminderFollowupBatchIn,
    PaymentReminderFollowupBatchResult,
    PaymentReminderFollowupIn,
)

router = APIRouter()


@router.get("/api/v1/shipments/payment-reminders")
def list_payment_reminders(
    scope: str = Query("todo"),
    customer: str | None = None,
    settlement_method: str | None = Query(None, alias="settlementMethod"),
    reminder_type: str | None = Query(None, alias="reminderType"),
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    return shipment_payment_followups_repo.list_reminders(
        scope=scope,
        customer=customer,
        settlement_method=settlement_method,
        reminder_type=reminder_type,
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
