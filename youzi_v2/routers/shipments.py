from fastapi import APIRouter

from ..context import *

router = APIRouter()

_SHIPMENT_EXPORT_MAX = 10_000

@router.get("/api/v1/shipments/filter-options")
def list_shipment_filter_options():
    return shipments_repo.list_filter_options()

@router.get("/api/v1/shipments/tracking-freshness-stats", response_model=TrackingFreshnessStats)
def get_shipment_tracking_freshness_stats():
    """全库轨迹新鲜度：内部/承运商分别统计今日、三日内（含今日）、更早、无。"""
    return TrackingFreshnessStats(**shipments_repo.tracking_freshness_stats())

@router.post("/api/v1/shipments/exceptions/open")
def open_shipment_exceptions(payload: ShipmentExceptionOpenIn):
    """批量标记异常（写入事件表并更新 exception_code）。"""
    nos = [n.strip() for n in payload.shipment_nos if n and n.strip()]
    if len(nos) > 200:
        raise HTTPException(status_code=400, detail="单次最多 200 个运单号")
    try:
        return shipment_exceptions_repo.open_for_shipment_nos(
            nos,
            payload.exception_code,
            note=payload.note,
            opened_time=payload.opened_time,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/api/v1/shipments/exceptions/close")
def close_shipment_exceptions(payload: ShipmentExceptionCloseIn):
    """批量解除当前异常。"""
    nos = [n.strip() for n in payload.shipment_nos if n and n.strip()]
    if len(nos) > 200:
        raise HTTPException(status_code=400, detail="单次最多 200 个运单号")
    try:
        return shipment_exceptions_repo.close_for_shipment_nos(
            nos,
            note=payload.note,
            closed_time=payload.closed_time,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/api/v1/shipments")
def list_shipments(
    search: str | None = None,
    tracking_search: str | None = Query(None, alias="trackingSearch"),
    shipment_nos: list[str] | None = Query(None, alias="shipmentNos"),
    status_code: str | None = Query(None, alias="statusCode"),
    exception_code: str | None = Query(None, alias="exceptionCode"),
    has_exception: bool | None = Query(None, alias="hasException"),
    customer: str | None = None,
    vip_only: bool | None = Query(None, alias="vipOnly"),
    carrier_code: str | None = Query(None, alias="carrierCode"),
    country_code: str | None = Query(None, alias="countryCode"),
    channel_code: str | None = Query(None, alias="channelCode"),
    channel_name_zh: str | None = Query(None, alias="channelNameZh"),
    channel_category: str | None = Query(None, alias="channelCategory"),
    vessel_voyage: str | None = Query(None, alias="vesselVoyage"),
    internal_freshness: str | None = Query(None, alias="internalFreshness"),
    carrier_freshness: str | None = Query(None, alias="carrierFreshness"),
    carrier_ahead_of_internal: bool | None = Query(None, alias="carrierAheadOfInternal"),
    min_stale_days: int | None = Query(None, alias="minStaleDays"),
    no_tracking: bool | None = Query(None, alias="noTracking"),
    limit: int = 100,
    offset: int = 0,
):
    if shipment_nos:
        cleaned = [n.strip() for n in shipment_nos if n and n.strip()]
        if len(cleaned) > 200:
            raise HTTPException(status_code=400, detail="单次最多查询 200 个单号")
        shipment_nos = cleaned
    try:
        result = shipments_repo.list_rows(
            search=search,
            tracking_search=tracking_search,
            shipment_nos=shipment_nos,
            status_code=status_code,
            exception_code=exception_code,
            has_exception=has_exception,
            customer=customer,
            vip_only=vip_only,
            carrier_code=carrier_code,
            country_code=country_code,
            channel_code=channel_code,
            channel_name_zh=channel_name_zh,
            channel_category=channel_category,
            vessel_voyage=vessel_voyage,
            internal_freshness=internal_freshness,
            carrier_freshness=carrier_freshness,
            carrier_ahead_of_internal=carrier_ahead_of_internal,
            min_stale_days=min_stale_days,
            no_tracking=no_tracking,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _apply_vip_flags(result.get("items") or [])
    return result

@router.post("/api/v1/shipments/{item_id}/subscribe")
def subscribe_shipment(item_id: str):
    try:
        return shipment_subscriptions_repo.subscribe(item_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="运单不存在")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.delete("/api/v1/shipments/{item_id}/subscribe")
def unsubscribe_shipment(item_id: str):
    shipment_subscriptions_repo.unsubscribe(item_id)
    return {"subscribed": False}

@router.get("/api/v1/shipment-subscriptions/notifications")
def list_shipment_subscription_notifications(limit: int = 20):
    """未读运单轨迹订阅通知（顶栏铃铛）。"""
    lim = max(1, min(limit, 50))
    return {
        "items": shipment_subscriptions_repo.list_unread_notifications(limit=lim),
        "unreadCount": shipment_subscriptions_repo.count_unread_notifications(),
    }

@router.post("/api/v1/shipment-subscriptions/notifications/read-all")
def mark_all_shipment_subscription_notifications_read():
    count = shipment_subscriptions_repo.mark_all_notifications_read()
    return {"count": count}

@router.post(
    "/api/v1/shipments/batch-subscribe",
    response_model=ShipmentSubscribeBatchResult,
)
def batch_subscribe_shipments(body: ShipmentBatchIdsIn):
    """批量订阅运单轨迹更新通知（内部/承运商最新轨迹变更时提醒）。"""
    return shipment_subscriptions_repo.subscribe_many(body.ids)

@router.post(
    "/api/v1/shipments/batch-unsubscribe",
    response_model=ShipmentUnsubscribeBatchResult,
)
def batch_unsubscribe_shipments(body: ShipmentBatchIdsIn):
    """批量取消运单轨迹订阅。"""
    return shipment_subscriptions_repo.unsubscribe_many(body.ids)

@router.get("/api/v1/shipments/export")
def export_shipments_excel(
    search: str | None = None,
    tracking_search: str | None = Query(None, alias="trackingSearch"),
    shipment_nos: list[str] | None = Query(None, alias="shipmentNos"),
    status_code: str | None = Query(None, alias="statusCode"),
    exception_code: str | None = Query(None, alias="exceptionCode"),
    has_exception: bool | None = Query(None, alias="hasException"),
    customer: str | None = None,
    vip_only: bool | None = Query(None, alias="vipOnly"),
    carrier_code: str | None = Query(None, alias="carrierCode"),
    country_code: str | None = Query(None, alias="countryCode"),
    channel_code: str | None = Query(None, alias="channelCode"),
    channel_name_zh: str | None = Query(None, alias="channelNameZh"),
    channel_category: str | None = Query(None, alias="channelCategory"),
    internal_freshness: str | None = Query(None, alias="internalFreshness"),
    carrier_freshness: str | None = Query(None, alias="carrierFreshness"),
    carrier_ahead_of_internal: bool | None = Query(None, alias="carrierAheadOfInternal"),
    min_stale_days: int | None = Query(None, alias="minStaleDays"),
    no_tracking: bool | None = Query(None, alias="noTracking"),
    limit: int = Query(_SHIPMENT_EXPORT_MAX, le=_SHIPMENT_EXPORT_MAX),
    offset: int = 0,
):
    """导出当前筛选条件下的运单列表（Excel，表头与导入模板一致）。"""
    if shipment_nos:
        cleaned = [n.strip() for n in shipment_nos if n and n.strip()]
        if len(cleaned) > 200:
            raise HTTPException(status_code=400, detail="单次最多查询 200 个单号")
        shipment_nos = cleaned
    try:
        result = shipments_repo.list_rows(
            search=search,
            tracking_search=tracking_search,
            shipment_nos=shipment_nos,
            status_code=status_code,
            exception_code=exception_code,
            has_exception=has_exception,
            customer=customer,
            vip_only=vip_only,
            carrier_code=carrier_code,
            country_code=country_code,
            channel_code=channel_code,
            channel_name_zh=channel_name_zh,
            channel_category=channel_category,
            internal_freshness=internal_freshness,
            carrier_freshness=carrier_freshness,
            carrier_ahead_of_internal=carrier_ahead_of_internal,
            min_stale_days=min_stale_days,
            no_tracking=no_tracking,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    total = int(result.get("total") or 0)
    if total > _SHIPMENT_EXPORT_MAX:
        raise HTTPException(
            status_code=400,
            detail=(
                f"当前筛选共 {total} 条，超过导出上限 {_SHIPMENT_EXPORT_MAX}，请缩小筛选范围"
            ),
        )
    data = build_export_excel_bytes(result.get("items") or [])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"运单导出_{ts}.xlsx"
    encoded = quote(filename)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )

@router.get("/api/v1/shipments/{item_id}/exception-events")
def list_shipment_exception_events(item_id: str, limit: int = 50, offset: int = 0):
    """运单异常事件历史（含已关闭记录的持续时间）。"""
    row = shipments_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="运单不存在")
    return shipment_exceptions_repo.list_by_shipment_no(
        row["shipmentNo"],
        limit=limit,
        offset=offset,
    )

@router.get("/api/v1/shipments/{item_id}/tracking-logs")
def list_shipment_internal_tracking_logs(item_id: str, limit: int = 20, offset: int = 0):
    """内部路由轨迹（internal_tracking_logs）。"""
    row = shipments_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="运单不存在")
    return internal_tracking_repo.list_by_shipment_no(
        row["shipmentNo"],
        limit=limit,
        offset=offset,
    )

@router.get("/api/v1/shipments/{item_id}/carrier-tracking-logs")
def list_shipment_carrier_tracking_logs(item_id: str, limit: int = 20, offset: int = 0):
    row = shipments_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="运单不存在")
    return carrier_tracking_repo.list_by_shipment_no(
        row["shipmentNo"],
        limit=limit,
        offset=offset,
    )

@router.get("/api/v1/shipments/tracking-sync/daily-stats")
def get_tracking_sync_daily_stats(source: str = Query("carrier")):
    src = source.strip().lower()
    if src not in ("internal", "carrier"):
        raise HTTPException(status_code=400, detail="source 须为 internal 或 carrier")
    return TrackingSyncDailyStats(**tracking_jobs_repo.today_stats(src))

@router.get("/api/v1/shipments/{item_id}")
def get_shipment(item_id: str):
    row = shipments_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="运单不存在")
    _apply_vip_flags([row])
    return row

@router.post("/api/v1/shipments")
def create_shipment(payload: ShipmentRecordIn):
    try:
        return shipments_repo.insert_row(payload.model_dump(by_alias=False))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="运单号已存在") from exc

@router.put("/api/v1/shipments/{item_id}")
def update_shipment(item_id: str, payload: ShipmentUpdateIn):
    try:
        return shipments_repo.update_row(item_id, payload.to_payload())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="运单不存在") from exc

@router.delete("/api/v1/shipments/{item_id}")
def delete_shipment(item_id: str):
    row = shipments_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="运单不存在")
    internal_tracking_repo.delete_by_shipment_no(row["shipmentNo"])
    carrier_tracking_repo.delete_by_shipment_no(row["shipmentNo"])
    shipments_repo.delete_row(item_id)
    return {"deleted": True}

@router.post("/api/v1/shipments/batch-delete", response_model=ShipmentBatchResult)
def batch_delete_shipments(body: ShipmentBatchIdsIn):
    """批量删除运单（含内部/承运商轨迹）；单次最多 200 条。"""
    ids = [i.strip() for i in body.ids if i and i.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")
    deleted = 0
    skipped: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for item_id in ids:
        row = shipments_repo.get_by_id(item_id)
        if row is None:
            skipped.append({"id": item_id, "shipmentNo": "", "message": "运单不存在"})
            continue
        sn = row["shipmentNo"]
        try:
            internal_tracking_repo.delete_by_shipment_no(sn)
            carrier_tracking_repo.delete_by_shipment_no(sn)
            if shipments_repo.delete_row(item_id):
                deleted += 1
            else:
                errors.append({"id": item_id, "shipmentNo": sn, "message": "删除失败"})
        except Exception as exc:
            errors.append({"id": item_id, "shipmentNo": sn, "message": str(exc)})
    return ShipmentBatchResult(
        total=len(ids),
        deleted=deleted,
        skipped=skipped,
        errors=errors,
    )

@router.patch("/api/v1/shipments/batch-update", response_model=ShipmentBatchResult)
def batch_update_shipments(body: ShipmentBatchUpdateIn):
    """批量修改运单字段（运单号不可改）；仅更新 updates 中提供的字段。"""
    ids = [i.strip() for i in body.ids if i and i.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")
    payload = body.updates.to_payload()
    if not payload:
        raise HTTPException(status_code=400, detail="请至少填写一项要修改的字段")
    updated = 0
    skipped: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for item_id in ids:
        row = shipments_repo.get_by_id(item_id)
        if row is None:
            skipped.append({"id": item_id, "shipmentNo": "", "message": "运单不存在"})
            continue
        try:
            shipments_repo.update_row(item_id, payload)
            updated += 1
        except KeyError:
            skipped.append(
                {
                    "id": item_id,
                    "shipmentNo": row.get("shipmentNo", ""),
                    "message": "运单不存在",
                }
            )
        except ValueError as exc:
            errors.append(
                {
                    "id": item_id,
                    "shipmentNo": row.get("shipmentNo", ""),
                    "message": str(exc),
                }
            )
    return ShipmentBatchResult(
        total=len(ids),
        updated=updated,
        skipped=skipped,
        errors=errors,
    )

@router.post("/api/v1/shipments/sync-tracking", response_model=TrackingSyncResult)
def sync_shipments_internal_tracking(body: TrackingSyncRequest | None = Body(None)):
    """
    从 config/config.json 的 base_url 拉取内部路由轨迹，
    写入 internal_tracking_logs。全库同步不含已签收；body.shipmentNos 指定单号时可含已签收。
    """
    shipment_nos: list[str] | None = None
    if body and body.shipment_nos:
        shipment_nos = [n.strip() for n in body.shipment_nos if n and n.strip()]
        if not shipment_nos:
            raise HTTPException(status_code=400, detail="运单号列表不能为空")
    try:
        return sync_all_tracking(
            shipments_repo,
            internal_tracking_repo,
            LOGISTICS_CONFIG_PATH,
            shipment_nos=shipment_nos,
            jobs_repo=tracking_jobs_repo,
            trigger="manual",
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"{exc}。请在仓库根目录 config/config.json 配置 base_url。",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower():
            raise HTTPException(
                status_code=503,
                detail="数据库繁忙（可能正在同步或迁移），请稍后重试。",
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/v1/shipments/sync-carrier-tracking", response_model=TrackingSyncResult)
def sync_shipments_carrier_tracking(body: TrackingSyncRequest | None = Body(None)):
    """
    按 config.vendors 匹配承运商并写入 carrier_tracking_logs。
    全库仅转运中；body.shipmentNos 指定单号时可含已签收。
    """
    shipment_nos: list[str] | None = None
    if body and body.shipment_nos:
        shipment_nos = [n.strip() for n in body.shipment_nos if n and n.strip()]
        if not shipment_nos:
            raise HTTPException(status_code=400, detail="运单号列表不能为空")
    try:
        return sync_carrier_tracking(
            shipments_repo,
            carrier_tracking_repo,
            tracking_jobs_repo,
            LOGISTICS_CONFIG_PATH,
            trigger="manual",
            shipment_nos=shipment_nos,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower():
            raise HTTPException(
                status_code=503,
                detail="数据库繁忙（可能正在同步或迁移），请稍后重试。",
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/v1/shipments/import")
async def import_shipments_excel(file: UploadFile = File(...)):
    """
    上传运单 Excel（表头与「运单数据」导出模板一致）。
    按运单号 upsert：已存在则更新，否则新增。
    """
    filename = (file.filename or "").lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 文件")

    task_id = str(uuid.uuid4())
    extension = Path(filename).suffix if Path(filename).suffix else ".xlsx"
    upload_path = UPLOAD_DIR / f"shipment_{task_id}{extension}"

    with upload_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        return import_excel_file(shipments_repo, upload_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if upload_path.exists():
            upload_path.unlink(missing_ok=True)
