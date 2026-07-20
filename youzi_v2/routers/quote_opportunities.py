from fastapi import APIRouter, HTTPException, Query

from ..context import *
from ..schemas.quote_opportunities import (
    QuoteExtendDeadlineIn,
    QuoteFollowupIn,
    QuoteMarkLostIn,
    QuoteOpportunityCreateIn,
    QuoteOpportunityPatchIn,
)

router = APIRouter()


def _create_payload(body: QuoteOpportunityCreateIn) -> dict:
    return {
        "customer_id": body.customer_id,
        "customer_name": body.customer_name,
        "is_new_customer": body.is_new_customer,
        "customer_inquiry_no": body.customer_inquiry_no,
        "quote_date": body.quote_date,
        "deadline_date": body.deadline_date,
        "followup_interval_days": body.followup_interval_days,
        "next_followup_date": body.next_followup_date,
        "owner": body.owner,
        "product_name": body.product_name,
        "address_text": body.address_text,
        "ctns": body.ctns,
        "weight_kg": body.weight_kg,
        "volume_cbm": body.volume_cbm,
        "quoted_amount": body.quoted_amount,
        "quoted_currency": body.quoted_currency,
        "profit_amount": body.profit_amount,
        "profit_currency": body.profit_currency,
        "profit_rate": body.profit_rate,
        "note": body.note,
    }


@router.get("/api/v1/quote-opportunities/notifications/summary")
def quote_opportunity_notification_summary():
    return quote_opportunities_repo.notification_summary()


@router.get("/api/v1/quote-opportunities")
def list_quote_opportunities(
    scope: str = Query("todo"),
    status: str | None = None,
    customer: str | None = None,
    is_new_customer: bool | None = Query(None, alias="isNewCustomer"),
    owner: str | None = None,
    quote_date_from: str | None = Query(None, alias="quoteDateFrom"),
    quote_date_to: str | None = Query(None, alias="quoteDateTo"),
    deadline_from: str | None = Query(None, alias="deadlineFrom"),
    deadline_to: str | None = Query(None, alias="deadlineTo"),
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    return quote_opportunities_repo.list_rows(
        scope=scope,
        status=status,
        customer=customer,
        is_new_customer=is_new_customer,
        owner=owner,
        quote_date_from=quote_date_from,
        quote_date_to=quote_date_to,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("/api/v1/quote-opportunities")
def create_quote_opportunity(body: QuoteOpportunityCreateIn):
    try:
        return quote_opportunities_repo.create(_create_payload(body))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/quote-opportunities/{quote_id}")
def get_quote_opportunity(quote_id: str):
    row = quote_opportunities_repo.get_by_id(quote_id)
    if row is None:
        raise HTTPException(status_code=404, detail="报价不存在")
    return row


@router.patch("/api/v1/quote-opportunities/{quote_id}")
def patch_quote_opportunity(quote_id: str, body: QuoteOpportunityPatchIn):
    data = body.model_dump(exclude_unset=True)
    payload = {
        "customer_id": data.get("customer_id"),
        "customer_name": data.get("customer_name"),
        "is_new_customer": data.get("is_new_customer"),
        "customer_inquiry_no": data.get("customer_inquiry_no"),
        "quote_date": data.get("quote_date"),
        "deadline_date": data.get("deadline_date"),
        "followup_interval_days": data.get("followup_interval_days"),
        "next_followup_date": data.get("next_followup_date"),
        "status": data.get("status"),
        "owner": data.get("owner"),
        "product_name": data.get("product_name"),
        "address_text": data.get("address_text"),
        "ctns": data.get("ctns"),
        "weight_kg": data.get("weight_kg"),
        "volume_cbm": data.get("volume_cbm"),
        "note": data.get("note"),
        "lost_reason": data.get("lost_reason"),
    }
    payload = {k: v for k, v in payload.items() if k in data}
    try:
        return quote_opportunities_repo.update(quote_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="报价不存在") from None


@router.post("/api/v1/quote-opportunities/{quote_id}/followups")
def create_quote_followup(quote_id: str, body: QuoteFollowupIn):
    version = None
    if body.adjust_quote and body.version is not None:
        version = {
            "change_reason": body.version.change_reason,
            "product_name": body.version.product_name,
            "address_text": body.version.address_text,
            "ctns": body.version.ctns,
            "weight_kg": body.version.weight_kg,
            "volume_cbm": body.version.volume_cbm,
            "quoted_amount": body.version.quoted_amount,
            "quoted_currency": body.version.quoted_currency,
            "profit_amount": body.version.profit_amount,
            "profit_currency": body.version.profit_currency,
            "profit_rate": body.version.profit_rate,
            "note": body.version.note,
        }
        # 仅传入客户端显式字段，避免覆盖现有摘要
        version = {
            k: v
            for k, v in version.items()
            if v is not None or k in ("change_reason", "note")
        }
    try:
        return quote_opportunities_repo.create_followup(
            quote_id,
            followup_type=body.followup_type,
            note=body.note,
            next_followup_date=body.next_followup_date,
            adjust_quote=body.adjust_quote,
            version=version,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="报价不存在") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/quote-opportunities/{quote_id}/versions")
def list_quote_versions(quote_id: str):
    if quote_opportunities_repo.get_by_id(quote_id) is None:
        raise HTTPException(status_code=404, detail="报价不存在")
    return {"items": quote_opportunities_repo.list_versions(quote_id)}


@router.get("/api/v1/quote-opportunities/{quote_id}/followups")
def list_quote_followups(quote_id: str):
    if quote_opportunities_repo.get_by_id(quote_id) is None:
        raise HTTPException(status_code=404, detail="报价不存在")
    return {"items": quote_opportunities_repo.list_followups(quote_id)}


@router.post("/api/v1/quote-opportunities/{quote_id}/mark-won")
def mark_quote_won(quote_id: str):
    try:
        return quote_opportunities_repo.mark_won(quote_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="报价不存在") from None


@router.post("/api/v1/quote-opportunities/{quote_id}/mark-lost")
def mark_quote_lost(quote_id: str, body: QuoteMarkLostIn):
    try:
        return quote_opportunities_repo.mark_lost(
            quote_id,
            lost_reason=body.lost_reason,
            note=body.note,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="报价不存在") from None


@router.post("/api/v1/quote-opportunities/{quote_id}/cancel")
def cancel_quote(quote_id: str):
    try:
        return quote_opportunities_repo.cancel(quote_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="报价不存在") from None


@router.post("/api/v1/quote-opportunities/{quote_id}/extend-deadline")
def extend_quote_deadline(quote_id: str, body: QuoteExtendDeadlineIn):
    try:
        return quote_opportunities_repo.extend_deadline(
            quote_id,
            deadline_date=body.deadline_date,
            next_followup_date=body.next_followup_date,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="报价不存在") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
