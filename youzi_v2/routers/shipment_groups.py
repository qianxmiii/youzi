from fastapi import APIRouter, HTTPException, Query, Response

from ..context import *

router = APIRouter()


@router.get("/api/v1/shipment-group-notifications")
def list_unread_shipment_group_notifications(limit: int = 20):
    """顶栏/首页：未读分组提醒列表与计数。"""
    lim = max(1, min(limit, 50))
    return {
        "items": shipment_group_alerts_repo.list_unread_notifications(limit=lim),
        "unreadCount": shipment_group_alerts_repo.count_unread(),
    }


@router.post(
    "/api/v1/shipment-groups/suggestions/preview",
    response_model=ShipmentGroupSuggestionsPreviewResult,
)
def preview_shipment_group_suggestions(body: ShipmentGroupSuggestionsPreviewIn):
    result = build_group_suggestions(_database, body.shipment_ids)
    return ShipmentGroupSuggestionsPreviewResult(
        suggestions=[
            ShipmentGroupSuggestionItem.model_validate(x)
            for x in result.get("suggestions") or []
        ],
        shipmentCount=int(result.get("shipmentCount") or 0),
        missingShipmentIds=list(result.get("missingShipmentIds") or []),
    )


@router.post(
    "/api/v1/shipment-groups/suggestions/apply",
    response_model=ShipmentGroupSuggestionsApplyResult,
)
def apply_shipment_group_suggestions(body: ShipmentGroupSuggestionsApplyIn):
    items = [item.model_dump(by_alias=False) for item in body.items]
    result = apply_group_suggestions(shipment_groups_repo, items)
    return ShipmentGroupSuggestionsApplyResult(**result)


@router.get("/api/v1/shipment-groups/meta")
def get_shipment_groups_meta():
    """分组类型等元数据（标签与说明）。"""
    from ..shipment_group_types import group_types_meta

    return {"groupTypes": group_types_meta()}


@router.get("/api/v1/shipment-groups")
def list_shipment_groups(
    search: str | None = None,
    group_type: str | None = Query(None, alias="groupType"),
    payment_status: str | None = Query(None, alias="paymentStatus"),
    customer: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    return shipment_groups_repo.list_rows(
        search=search,
        group_type=group_type,
        payment_status=payment_status,
        customer=customer,
        limit=limit,
        offset=offset,
    )


@router.post("/api/v1/shipment-groups", status_code=201)
def create_shipment_group(body: ShipmentGroupIn):
    try:
        primary, types = body.resolve_types()
        return shipment_groups_repo.create(
            group_no=body.group_no,
            group_name=body.group_name,
            primary_type=primary,
            group_types=types,
            customer=body.customer,
            customer_no=body.customer_no,
            vessel_voyage=body.vessel_voyage,
            destination_port_code=body.destination_port_code,
            payment_status=body.payment_status,
            payment_due_rule=body.payment_due_rule,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/shipment-groups/{item_id}")
def get_shipment_group(item_id: str):
    row = shipment_groups_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="分组不存在")
    return row


@router.put("/api/v1/shipment-groups/{item_id}")
def update_shipment_group(item_id: str, body: ShipmentGroupUpdateIn):
    data = body.model_dump(exclude_unset=True, by_alias=False)
    if not data:
        row = shipment_groups_repo.get_by_id(item_id)
        if row is None:
            raise HTTPException(status_code=404, detail="分组不存在")
        return row
    try:
        row = shipment_groups_repo.update(item_id, **data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="分组不存在")
    return row


@router.delete("/api/v1/shipment-groups/{item_id}", status_code=204)
def delete_shipment_group(item_id: str):
    if not shipment_groups_repo.delete(item_id):
        raise HTTPException(status_code=404, detail="分组不存在")
    return Response(status_code=204)


@router.post(
    "/api/v1/shipment-groups/{item_id}/members",
    response_model=ShipmentGroupMembersAddResult,
)
def add_shipment_group_members(item_id: str, body: ShipmentGroupMembersAddIn):
    try:
        result = shipment_groups_repo.add_members(
            item_id,
            body.shipment_ids,
            role=body.role,
            batch_no=body.batch_no,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="分组不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ShipmentGroupMembersAddResult(**result)


@router.delete(
    "/api/v1/shipment-groups/{item_id}/members",
    response_model=ShipmentGroupMembersRemoveResult,
)
def remove_shipment_group_members(item_id: str, body: ShipmentGroupMembersRemoveIn):
    try:
        result = shipment_groups_repo.remove_members(item_id, body.shipment_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="分组不存在") from exc
    return ShipmentGroupMembersRemoveResult(**result)


@router.patch(
    "/api/v1/shipment-groups/{item_id}/members/batch",
    response_model=ShipmentGroupMembersBatchPatchResult,
)
def patch_shipment_group_members_batch(
    item_id: str,
    body: ShipmentGroupMembersBatchPatchIn,
):
    items = [
        {
            "shipment_id": item.shipment_id,
            "role": item.role,
            "batch_no": item.batch_no,
        }
        for item in body.items
    ]
    try:
        result = shipment_groups_repo.patch_members_batch(item_id, items)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="分组不存在") from exc
    return ShipmentGroupMembersBatchPatchResult(**result)


@router.get("/api/v1/shipment-groups/{item_id}/notifications")
def list_shipment_group_notifications(
    item_id: str,
    unread_only: bool = Query(False, alias="unreadOnly"),
    limit: int = 50,
    offset: int = 0,
):
    if shipment_groups_repo.get_by_id(item_id, include_members=False) is None:
        raise HTTPException(status_code=404, detail="分组不存在")
    return shipment_group_alerts_repo.list_notifications(
        item_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/api/v1/shipment-groups/{item_id}/evaluate-alerts",
    response_model=ShipmentGroupEvaluateResult,
)
def evaluate_shipment_group_alerts(item_id: str):
    if shipment_groups_repo.get_by_id(item_id, include_members=False) is None:
        raise HTTPException(status_code=404, detail="分组不存在")
    result = evaluate_group_alerts(
        _database,
        shipment_group_alerts_repo,
        group_id=item_id,
    )
    return ShipmentGroupEvaluateResult(**result)


@router.post(
    "/api/v1/shipment-group-notifications/{notification_id}/read",
    response_model=ShipmentGroupNotificationReadResult,
)
def mark_shipment_group_notification_read(notification_id: str):
    if not shipment_group_alerts_repo.mark_read(notification_id):
        raise HTTPException(status_code=404, detail="提醒不存在或已读")
    return ShipmentGroupNotificationReadResult(count=1)


@router.post(
    "/api/v1/shipment-group-notifications/{notification_id}/resolve",
    response_model=ShipmentGroupNotificationReadResult,
)
def resolve_shipment_group_notification(notification_id: str):
    if not shipment_group_alerts_repo.mark_resolved(notification_id):
        raise HTTPException(status_code=404, detail="提醒不存在或已处理")
    return ShipmentGroupNotificationReadResult(count=1)


@router.post(
    "/api/v1/shipment-group-notifications/read-all",
    response_model=ShipmentGroupNotificationReadResult,
)
def mark_all_shipment_group_notifications_read(
    group_id: str | None = Query(None, alias="groupId"),
):
    count = shipment_group_alerts_repo.mark_all_read(group_id)
    return ShipmentGroupNotificationReadResult(count=count)
