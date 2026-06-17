from fastapi import APIRouter

from ..context import *

router = APIRouter()

@router.post("/api/v1/vessel-schedules/port-calls/{port_call_id}/subscribe")
def subscribe_port_call(port_call_id: str):
    try:
        return port_subscriptions_repo.subscribe(port_call_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="挂靠港不存在")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.delete("/api/v1/vessel-schedules/port-calls/{port_call_id}/subscribe")
def unsubscribe_port_call(port_call_id: str):
    port_subscriptions_repo.unsubscribe(port_call_id)
    return {"subscribed": False}

@router.get("/api/v1/vessel-schedules")
def list_vessel_schedules(
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    return vessel_schedules_repo.list_rows(search=search, limit=limit, offset=offset)

@router.get("/api/v1/vessel-schedules/template")
def download_vessel_schedule_template():
    data = build_vessel_schedule_template_bytes()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="vessel_schedule_template.xlsx"'},
    )

@router.get("/api/v1/vessel-schedules/providers")
def list_vessel_schedule_providers():
    """已接入的船期拉取 Provider（按船公司路由）。"""
    return {"items": list_schedule_providers()}

@router.get("/api/v1/vessel-schedules/vessels/search")
def search_carrier_vessel_names(
    shipping_company: str = Query(..., alias="shippingCompany", min_length=1),
    prefix: str = Query(..., min_length=3),
):
    """按船公司检索船舶（如 COSCO 船名前缀 → vesselCode）。"""
    try:
        items = search_carrier_vessels(shipping_company, prefix)
        return {"items": items}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/api/v1/vessel-schedules/fetch/preview")
def preview_external_vessel_schedule(
    shipping_company: str = Query(..., alias="shippingCompany", min_length=1),
    vessel_code: str = Query(..., alias="vesselCode", min_length=1),
    period: int = Query(28, ge=7, le=90),
):
    """按船公司 + 船舶代码预览挂靠（不落库）。"""
    try:
        return fetch_vessel_schedule(
            shipping_company,
            vessel_code,
            period=period,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/api/v1/vessel-schedules/fetch/sync")
def sync_external_vessel_schedule(body: VesselScheduleFetchIn):
    """从船公司接口拉取船期并 upsert 到航次主数据。"""
    try:
        return sync_one_vessel_schedule(
            vessel_schedules_repo,
            body.shipping_company,
            body.vessel_code,
            period=body.period,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post(
    "/api/v1/vessel-schedules/fetch/sync-all",
    response_model=VesselScheduleSyncAllResult,
)
def sync_all_external_vessel_schedules(
    body: VesselScheduleSyncAllIn = Body(default_factory=VesselScheduleSyncAllIn),
):
    """同步库内所有已配置船公司 + 船舶代码的航次挂靠。"""
    return sync_all_vessel_schedules(
        vessel_schedules_repo,
        period=body.period,
    )

@router.get("/api/v1/vessel-schedules/{voyage_id}")
def get_vessel_schedule(voyage_id: str):
    row = vessel_schedules_repo.get_detail(voyage_id)
    if not row:
        raise HTTPException(status_code=404, detail="航次不存在")
    return row

@router.get("/api/v1/vessel-schedules/{voyage_id}/shipments")
def list_vessel_schedule_shipments(
    voyage_id: str,
    maritime_status: str | None = Query(None, alias="maritimeStatus"),
    limit: int = 200,
    offset: int = 0,
):
    row = vessel_schedules_repo.get_detail(voyage_id)
    if not row:
        raise HTTPException(status_code=404, detail="航次不存在")
    return vessel_schedules_repo.list_shipments_for_voyage(
        row["vesselVoyage"],
        vessel_name=row.get("vesselName"),
        voyage_no=row.get("voyageNo"),
        maritime_status=maritime_status,
        limit=limit,
        offset=offset,
    )

@router.post("/api/v1/vessel-schedules", status_code=201)
def create_vessel_schedule(body: VesselVoyageIn):
    try:
        return vessel_schedules_repo.create(
            body.model_dump(by_alias=False, exclude_none=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.patch("/api/v1/vessel-schedules/{voyage_id}")
def update_vessel_schedule(voyage_id: str, body: VesselVoyageUpdateIn):
    try:
        return vessel_schedules_repo.update(
            voyage_id,
            body.model_dump(by_alias=False, exclude_unset=True, exclude_none=True),
        )
    except ValueError as exc:
        status = 404 if "不存在" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc

@router.delete("/api/v1/vessel-schedules/{voyage_id}", status_code=204)
def delete_vessel_schedule(voyage_id: str):
    try:
        vessel_schedules_repo.delete(voyage_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)

@router.post("/api/v1/vessel-schedules/import", response_model=VoyageImportResult)
async def import_vessel_schedules_excel(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 文件")
    task_id = str(uuid.uuid4())
    extension = Path(filename).suffix if Path(filename).suffix else ".xlsx"
    upload_path = UPLOAD_DIR / f"vessel_schedule_{task_id}{extension}"
    with upload_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        return import_vessel_schedule_excel(vessel_schedules_repo, upload_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if upload_path.exists():
            upload_path.unlink(missing_ok=True)
