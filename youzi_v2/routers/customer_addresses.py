"""客户地址簿。"""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile

from ..context import UPLOAD_DIR, customer_addresses_repo
from ..schemas.customer_addresses import CustomerAddressBatchDeleteIn, CustomerAddressIn
from ..services.customer_address_excel import (
    build_export_bytes,
    build_template_bytes,
    import_excel_file,
)

router = APIRouter()

_EXPORT_MAX = 10_000


def _list_query(
    customer: str | None,
    address_kind: str | None,
    remote: bool | None,
    search: str | None,
    limit: int,
    offset: int,
):
    try:
        return customer_addresses_repo.list_rows(
            customer=customer,
            address_kind=address_kind,
            remote=remote,
            search=search,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/customer-addresses")
def list_customer_addresses(
    customer: str | None = None,
    address_kind: str | None = Query(None, alias="addressKind"),
    remote: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    return _list_query(customer, address_kind, remote, search, limit, offset)


@router.get("/api/v1/customer-addresses/export")
def export_customer_addresses(
    customer: str | None = None,
    address_kind: str | None = Query(None, alias="addressKind"),
    remote: bool | None = None,
    search: str | None = None,
):
    result = _list_query(customer, address_kind, remote, search, _EXPORT_MAX, 0)
    total = int(result.get("total") or 0)
    if total > _EXPORT_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"当前筛选共 {total} 条，超过导出上限 {_EXPORT_MAX}，请缩小筛选范围",
        )
    data = build_export_bytes(result.get("items") or [])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"客户地址导出_{ts}.xlsx"
    encoded = quote(filename)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get("/api/v1/customer-addresses/template")
def download_customer_address_template():
    data = build_template_bytes()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="customer_address_template.xlsx"'
        },
    )


@router.post("/api/v1/customer-addresses/import")
async def import_customer_addresses(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 文件")
    upload_path = UPLOAD_DIR / f"customer_address_{uuid.uuid4().hex}.xlsx"
    with upload_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    try:
        return import_excel_file(customer_addresses_repo, upload_path)
    finally:
        upload_path.unlink(missing_ok=True)


@router.post("/api/v1/customer-addresses/batch-delete")
def batch_delete_customer_addresses(body: CustomerAddressBatchDeleteIn):
    try:
        return customer_addresses_repo.delete_many(body.ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/v1/customer-addresses", status_code=201)
def create_customer_address(body: CustomerAddressIn):
    try:
        return customer_addresses_repo.insert_row(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/v1/customer-addresses/{item_id}")
def update_customer_address(item_id: str, body: CustomerAddressIn):
    try:
        return customer_addresses_repo.update_row(item_id, body.model_dump())
    except KeyError:
        raise HTTPException(status_code=404, detail="地址不存在") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/v1/customer-addresses/{item_id}")
def delete_customer_address(item_id: str):
    deleted = customer_addresses_repo.delete_row(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="地址不存在")
    return {"deleted": True}
