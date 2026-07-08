from fastapi import APIRouter, HTTPException, Query

from ..context import *

router = APIRouter()


@router.get("/api/v1/channels/{code}/sla-rules")
def list_channel_sla_rules(code: str):
    if channels_repo.get_row(code) is None:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return {"items": channel_sla_rules_repo.list_by_channel(code)}


@router.put("/api/v1/channels/{code}/sla-rules")
def upsert_channel_sla_rule(code: str, body: ChannelSlaRuleIn):
    if channels_repo.get_row(code) is None:
        raise HTTPException(status_code=404, detail="渠道不存在")
    try:
        row = channel_sla_rules_repo.upsert_rule(
            channel_code=code,
            estimated_days=body.estimated_days,
            carrier_code=body.carrier_code,
            start_field=body.start_field,
            warning_days=body.warning_days,
            severe_overdue_days=body.severe_overdue_days,
            enabled=body.enabled,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return row


@router.delete("/api/v1/channels/{code}/sla-rules/{rule_id}", status_code=204)
def delete_channel_sla_rule(code: str, rule_id: str):
    rules = channel_sla_rules_repo.list_by_channel(code)
    if not any(r["id"] == rule_id for r in rules):
        raise HTTPException(status_code=404, detail="规则不存在")
    channel_sla_rules_repo.delete_rule(rule_id)
    return Response(status_code=204)


@router.get("/api/v1/shipment-sla-alerts")
def list_shipment_sla_alerts(
    scope: str = Query("todo", description="todo=默认待办（未签收且 open/acknowledged）；all=含历史"),
    risk_level: str | None = Query(None, alias="riskLevel"),
    alert_type: str | None = Query(None, alias="alertType"),
    status: str | None = None,
    has_exception: bool | None = Query(None, alias="hasException"),
    exception_code: str | None = Query(None, alias="exceptionCode"),
    channel_code: str | None = Query(None, alias="channelCode"),
    carrier_code: str | None = Query(None, alias="carrierCode"),
    customer: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    return shipment_sla_alerts_repo.list_alerts(
        scope=scope,
        risk_level=risk_level,
        alert_type=alert_type,
        status=status,
        has_exception=has_exception,
        exception_code=exception_code,
        channel_code=channel_code,
        carrier_code=carrier_code,
        customer=customer,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/api/v1/shipment-sla-alerts/summary")
def get_shipment_sla_alerts_summary():
    return shipment_sla_alerts_repo.summary_counts()


@router.get("/api/v1/shipment-sla-alerts/todo-notifications")
def list_shipment_sla_todo_notifications(limit: int = 20):
    lim = max(1, min(limit, 50))
    return {
        "items": shipment_sla_alerts_repo.list_todo_notifications(limit=lim),
        "pendingCount": shipment_sla_alerts_repo.count_todo(),
    }


@router.post("/api/v1/shipment-sla-alerts/evaluate", response_model=ShipmentSlaScanResult)
def evaluate_shipment_sla_alerts():
    result = scan_shipment_sla_alerts(
        shipment_sla_alerts_repo,
        channel_sla_rules_repo,
        shipment_exception_followup_repo,
        force=True,
        trigger="manual",
    )
    return ShipmentSlaScanResult(**result)


@router.post("/api/v1/shipment-sla-alerts/{alert_id}/follow-up")
def follow_up_shipment_sla_alert(alert_id: str):
    if not shipment_sla_alerts_repo.follow_up(alert_id):
        raise HTTPException(status_code=404, detail="预警不存在或不可跟进")
    return {"ok": True}


@router.post("/api/v1/shipment-sla-alerts/{alert_id}/acknowledge")
def acknowledge_shipment_sla_alert(alert_id: str):
    if not shipment_sla_alerts_repo.follow_up(alert_id):
        raise HTTPException(status_code=404, detail="预警不存在或不可跟进")
    return {"ok": True}


@router.post("/api/v1/shipment-sla-alerts/{alert_id}/resolve")
def resolve_shipment_sla_alert(alert_id: str):
    if not shipment_sla_alerts_repo.resolve_alert(alert_id):
        raise HTTPException(status_code=404, detail="预警不存在或不可解决")
    return {"ok": True}


@router.post("/api/v1/shipment-sla-alerts/{alert_id}/ignore")
def ignore_shipment_sla_alert(alert_id: str):
    if not shipment_sla_alerts_repo.ignore(alert_id):
        raise HTTPException(status_code=404, detail="预警不存在或已结案")
    return {"ok": True}


@router.post("/api/v1/shipment-sla-alerts/{alert_id}/convert")
def convert_shipment_sla_alert(alert_id: str, body: ShipmentSlaAlertConvertIn):
    alert = shipment_sla_alerts_repo.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")
    if alert["status"] not in ("open", "acknowledged"):
        raise HTTPException(status_code=400, detail="该预警已不可转异常")

    shipment_no = alert["shipmentNo"]
    open_result = shipment_exceptions_repo.open_for_shipment_nos(
        [shipment_no],
        body.exception_code,
        note=body.note or None,
    )
    if open_result.get("errors"):
        err = open_result["errors"][0]
        raise HTTPException(status_code=400, detail=err.get("message", "转异常失败"))
    if not open_result.get("opened") and open_result.get("skipped"):
        pass

    events = shipment_exceptions_repo.list_by_shipment_no(shipment_no, limit=1)
    event_id = events["items"][0]["id"] if events.get("items") else ""

    if not shipment_sla_alerts_repo.mark_converted(
        alert_id,
        exception_code=body.exception_code,
        event_id=event_id,
    ):
        raise HTTPException(status_code=400, detail="更新预警状态失败")
    return {"ok": True, "eventId": event_id}


@router.patch("/api/v1/shipment-sla-alerts/{alert_id}/note")
def update_shipment_sla_alert_note(alert_id: str, body: ShipmentSlaAlertNoteIn):
    if not shipment_sla_alerts_repo.update_note(alert_id, body.note):
        raise HTTPException(status_code=404, detail="预警不存在")
    return {"ok": True}
