from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from ..context import _database, DATA_DIR
from ..services import link_download as service
router = APIRouter(tags=['link-download'])
ROOT = DATA_DIR / 'link_downloads'
class DownloadRow(BaseModel):
    shipmentNo: str = Field(min_length=1,max_length=100)
    url: str = Field(min_length=1,max_length=3000)
class DownloadIn(BaseModel):
    rows: list[DownloadRow] = Field(min_length=1,max_length=100)
@router.get('/api/v1/tools/link-download/rules')
def rules():
    return {'items':service.RULES}

@router.post('/api/v1/tools/link-download/jobs')
def create(body: DownloadIn):
    try: return service.create_job(_database,ROOT,[r.model_dump() for r in body.rows])
    except ValueError as exc: raise HTTPException(400,str(exc)) from None
@router.get('/api/v1/tools/link-download/jobs')
def history():
    return {'items':service.list_jobs(_database)}
@router.get('/api/v1/tools/link-download/jobs/{job_id}')
def get(job_id: str):
    try: return service.get_job(_database,job_id)
    except KeyError: raise HTTPException(404,'任务不存在') from None
@router.post('/api/v1/tools/link-download/jobs/{job_id}/retry')
def retry(job_id: str):
    try:
        job = service.get_job(_database,job_id)
        if job['status']=='running': raise ValueError('请等待本批次完成')
        failed = [r for r in job['rows'] if r['status']=='failed']
        return service.create_job(_database,ROOT,failed)
    except KeyError: raise HTTPException(404,'任务不存在') from None
    except ValueError as exc: raise HTTPException(400,str(exc)) from None
@router.get('/api/v1/tools/link-download/jobs/{job_id}/download')
def download(job_id: str, index: int | None = None):
    try:
        path,name = service.download_path(_database,ROOT,job_id,index)
        return FileResponse(path,media_type='application/zip',filename=name)
    except KeyError: raise HTTPException(404,'任务不存在') from None
    except ValueError as exc: raise HTTPException(409,str(exc)) from None
