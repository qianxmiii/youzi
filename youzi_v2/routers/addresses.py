from fastapi import APIRouter

from ..context import *

router = APIRouter()

_ADDRESS_EXPORT_MAX = 10_000

@router.get("/api/addresses")
def get_addresses(
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
):
    """第三方海外仓 / 商私地址（Legacy）。未传 limit 时返回数组。"""
    result = addresses_repo.list_rows(search=search, limit=limit, offset=offset)
    if limit is None:
        return result["items"]
    return result

@router.post("/api/addresses")
def create_address(payload: LegacyAddressRecordIn):
    return addresses_repo.insert_row(payload.model_dump(by_alias=False))

@router.put("/api/addresses/{item_id}")
def update_address(item_id: str, payload: LegacyAddressRecordIn):
    try:
        return addresses_repo.update_row(item_id, payload.model_dump(by_alias=False))
    except KeyError:
        raise HTTPException(status_code=404, detail="记录不存在")

@router.delete("/api/addresses/{item_id}")
def delete_address(item_id: str):
    deleted = addresses_repo.delete_row(item_id)
    return {"deleted": deleted}

@router.get("/api/addresses-warehouse/filter-options")
def get_warehouse_address_filter_options():
    """平台仓库地址筛选项。"""
    return addresses_warehouse_repo.list_filter_options()

@router.get("/api/addresses-warehouse")
def get_warehouse_addresses(
    search: str | None = None,
    address_type: str | None = Query(None, alias="addressType"),
    country_code: str | None = Query(None, alias="countryCode"),
    limit: int | None = None,
    offset: int = 0,
):
    """平台仓库地址簿（AMZ / WFS）。"""
    return addresses_warehouse_repo.list_rows(
        search=search,
        address_type=address_type,
        country_code=country_code,
        limit=limit,
        offset=offset,
    )

@router.post("/api/addresses-warehouse")
def create_warehouse_address(payload: WarehouseAddressRecordIn):
    try:
        return addresses_warehouse_repo.insert_row(payload.model_dump(by_alias=False))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.put("/api/addresses-warehouse/{item_id}")
def update_warehouse_address(item_id: str, payload: WarehouseAddressRecordIn):
    try:
        return addresses_warehouse_repo.update_row(item_id, payload.model_dump(by_alias=False))
    except KeyError:
        raise HTTPException(status_code=404, detail="记录不存在")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.delete("/api/addresses-warehouse/{item_id}")
def delete_warehouse_address(item_id: str):
    deleted = addresses_warehouse_repo.delete_row(item_id)
    return {"deleted": deleted}

@router.get("/api/addresses-warehouse/template")
def download_warehouse_address_template():
    data = build_address_template_bytes()
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="address_warehouse_template.xlsx"'},
    )

@router.get("/api/addresses-warehouse/export")
def export_warehouse_addresses_excel(
    search: str | None = None,
    address_type: str | None = Query(None, alias="addressType"),
    country_code: str | None = Query(None, alias="countryCode"),
    limit: int = Query(_ADDRESS_EXPORT_MAX, le=_ADDRESS_EXPORT_MAX),
    offset: int = 0,
):
    """导出平台仓库地址（Excel，表头与导入模板一致）。"""
    result = addresses_warehouse_repo.list_rows(
        search=search,
        address_type=address_type,
        country_code=country_code,
        limit=limit,
        offset=offset,
    )
    total = int(result.get("total") or 0)
    if total > _ADDRESS_EXPORT_MAX:
        raise HTTPException(
            status_code=400,
            detail=(
                f"当前筛选共 {total} 条，超过导出上限 {_ADDRESS_EXPORT_MAX}，请缩小筛选范围"
            ),
        )
    data = build_address_export_bytes(result.get("items") or [])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"仓库地址导出_{ts}.xlsx"
    encoded = quote(filename)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )

@router.post("/api/addresses-warehouse/import")
async def import_warehouse_addresses_excel(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 文件")
    task_id = str(uuid.uuid4())
    extension = Path(filename).suffix if Path(filename).suffix else ".xlsx"
    upload_path = UPLOAD_DIR / f"address_warehouse_{task_id}{extension}"
    with upload_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        return import_address_excel(addresses_warehouse_repo, upload_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if upload_path.exists():
            upload_path.unlink(missing_ok=True)
