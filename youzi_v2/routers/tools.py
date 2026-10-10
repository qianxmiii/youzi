"""常用工具 API。"""

from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from ..services.image_link_zip import image_zip_jobs
from ..services.product_import_convert import (
    convert_invoice_to_product_import,
    product_import_output_path,
)
from ..services.shipment_file_rename import parse_shipment_rename_excel

router = APIRouter()

_MAX_UPLOAD = 30 * 1024 * 1024


@router.post("/api/v1/tools/image-link-zip/jobs")
async def start_image_link_zip_job(
    file: UploadFile = File(...),
    column: str = Query("P", description="图片链接所在列（字母，默认 P）"),
):
    """上传 Excel，启动后台下载任务，立即返回 jobId（可轮询进度）。"""
    filename = (file.filename or "").strip() or "upload.xls"
    lower = filename.lower()
    if not (lower.endswith(".xls") or lower.endswith(".xlsx") or lower.endswith(".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 .xls / .xlsx 文件")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=400, detail="文件过大（上限 30MB）")

    try:
        job = image_zip_jobs.create(data, filename=filename, column=column)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"创建任务失败：{exc}") from exc

    return job.to_api()


@router.get("/api/v1/tools/image-link-zip/jobs/{job_id}")
def get_image_link_zip_job(job_id: str):
    job = image_zip_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return job.to_api()


@router.get("/api/v1/tools/image-link-zip/jobs/{job_id}/download")
def download_image_link_zip_job(job_id: str):
    job = image_zip_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    if job.status == "failed":
        raise HTTPException(status_code=400, detail=job.error or "打包失败")
    if job.status != "done" or not job.zip_bytes:
        raise HTTPException(status_code=409, detail="尚未完成，请稍后下载")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"标签图片_{ts}.zip"
    encoded = quote(out_name)
    return Response(
        content=job.zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "X-Image-Zip-Total": str(job.total),
            "X-Image-Zip-Downloaded": str(job.downloaded),
            "X-Image-Zip-Failed": str(job.failed),
        },
    )


@router.post("/api/v1/tools/shipment-file-rename/parse")
async def parse_shipment_file_rename_excel(file: UploadFile = File(...)):
    """解析运单 Excel，返回「运单号 → 目标文件名主干」映射（不改本地文件）。"""
    filename = (file.filename or "").strip() or "upload.xlsx"
    lower = filename.lower()
    if not (lower.endswith(".xls") or lower.endswith(".xlsx") or lower.endswith(".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 .xls / .xlsx 文件")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=400, detail="文件过大（上限 30MB）")

    try:
        return parse_shipment_rename_excel(data, filename=filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"解析失败：{exc}") from exc


@router.post("/api/v1/tools/product-import")
async def product_import_convert(invoice: UploadFile = File(...)):
    """上传箱单发票，转换为产品导入模版（.xls）。"""
    filename = (invoice.filename or "").strip() or "invoice.xlsx"
    lower = filename.lower()
    if not (lower.endswith(".xls") or lower.endswith(".xlsx") or lower.endswith(".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 .xls / .xlsx 箱单文件")

    data = await invoice.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=400, detail="文件过大（上限 30MB）")

    suffix = Path(filename).suffix or ".xlsx"
    try:
        result = convert_invoice_to_product_import(data, suffix=suffix)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"转换失败：{exc}") from exc
    return {"ok": True, **result}


@router.get("/api/v1/tools/product-import/download/{task_id}")
def product_import_download(task_id: str):
    if len(task_id) < 8:
        raise HTTPException(status_code=400, detail="无效 ID")
    output_path = product_import_output_path(task_id)
    if not output_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.ms-excel",
        filename="产品导入模版.xls",
    )
