from fastapi import APIRouter

from ..context import *

router = APIRouter()

@router.get("/api/quote-history")
def get_quote_history():
    return quote_history_repo.list_rows()

@router.post("/api/quote-history")
def create_quote_history(payload: QuoteRecordIn):
    return quote_history_repo.insert_admin_simple(
        payload.customer,
        payload.channel,
        payload.amount,
        payload.note,
        product_name=payload.product_name,
        address=payload.address,
        country=payload.country,
    )

@router.post("/api/quote-history/index")
def create_quote_from_index_page(payload: dict[str, Any] = Body(...)):
    """供 index.html 写入完整报价快照（与 logistics.js quoteData 字段一致）。"""
    return quote_history_repo.insert_from_index_payload(payload)

@router.put("/api/quote-history/{item_id}")
def update_quote_history(item_id: str, payload: QuoteRecordIn):
    try:
        return quote_history_repo.update_admin_simple(
            item_id,
            payload.customer,
            payload.channel,
            payload.amount,
            payload.note,
            product_name=payload.product_name,
            address=payload.address,
            country=payload.country,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="记录不存在")

@router.delete("/api/quote-history/{item_id}")
def delete_quote_history(item_id: str):
    deleted = quote_history_repo.delete(item_id)
    return {"deleted": deleted}

@router.delete("/api/quote-history")
def clear_quote_history():
    quote_history_repo.clear()
    return {"ok": True}

@router.post("/api/product-import")
async def product_import(invoice: UploadFile = File(...)):
    filename = (invoice.filename or "").lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 文件")

    data = await invoice.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")
    suffix = Path(filename).suffix or ".xlsx"
    try:
        from ..services.product_import_convert import convert_invoice_to_product_import

        result = convert_invoice_to_product_import(data, suffix=suffix)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"转换失败：{exc}") from exc
    return {"ok": True, "id": result["id"], "filename": result["filename"]}

@router.get("/api/product-import/download/{task_id}")
def download_file(task_id: str):
    if len(task_id) < 8:
        raise HTTPException(status_code=400, detail="无效 ID")

    output_path = OUTPUT_DIR / f"{task_id}.xls"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.ms-excel",
        filename="产品导入模版.xls",
    )
