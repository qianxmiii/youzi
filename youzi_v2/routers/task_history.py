from typing import Literal
import json
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from ..context import _database
from ..db.task_history import save_task, list_tasks, list_events
router = APIRouter(tags=['task-history'])

class TaskHistoryIn(BaseModel):
    id: str = Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9-]+$')
    title: str = Field(max_length=200)
    started: int = Field(ge=0)
    finished: int | None = None
    state: Literal['running','done','failed']
    progress: float | None = Field(default=None, ge=0, le=100)
    message: str = Field(default='', max_length=20000)
    details: str = Field(default='', max_length=300000)
    stats: list[dict] | None = Field(default=None, max_length=30)
    rows: list[dict] | None = Field(default=None, max_length=10000)
    resultKind: str | None = None
    source: str | None = Field(default=None, max_length=200)
    sourcePath: str | None = Field(default=None, max_length=1000)

@router.put('/api/v1/task-history/{task_id}')
def update_task(task_id: str, body: TaskHistoryIn):
    if task_id != body.id:
        raise HTTPException(400, '任务编号不一致')
    with _database.lock:
        existing = _database.conn.execute('SELECT payload FROM task_history WHERE id=?',(task_id,)).fetchone()
    if existing and json.loads(existing[0]).get('managedBy') in ('server','request'):
        raise HTTPException(409, '后端任务记录不能由前端覆盖')
    task = body.model_dump(exclude_none=True)
    if len(json.dumps(task)) > 2000000:
        raise HTTPException(413, '任务记录过大')
    save_task(_database, task)
    return {'ok':True}

@router.get('/api/v1/task-history')
def history(limit: int = Query(50,ge=1,le=100), offset: int = Query(0,ge=0)):
    from ..services.link_download import list_jobs
    list_jobs(_database)
    from ..services.request_task_tracking import active_ids
    return {'items':list_tasks(_database,limit,offset), 'activeRequestIds':active_ids()}

@router.get('/api/v1/task-history/{task_id}/events')
def events(task_id: str):
    return {'items':list_events(_database,task_id)}


@router.delete('/api/v1/task-history/{task_id}')
def remove_task(task_id: str):
    from ..db.task_history import delete_task
    try: delete_task(_database,task_id)
    except KeyError: raise HTTPException(404,'记录不存在') from None
    except ValueError as exc: raise HTTPException(409,str(exc)) from None
    return {'ok':True}
