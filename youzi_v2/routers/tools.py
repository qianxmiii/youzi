"""常用工具 API。"""

from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from ..services.image_link_zip import image_zip_jobs

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
