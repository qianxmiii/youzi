from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel,Field
from ..context import shipments_repo,LOGISTICS_CONFIG_PATH
from ..services.commerce_marks import settings,apply_marks,load_catalog,migrate_legacy_catalog
router=APIRouter(tags=['commerce-marks'])
class MarksIn(BaseModel):
    ids:list[str]=Field(min_length=1,max_length=200)
    markIds:list[str]=Field(default_factory=list,max_length=100)
    type:int=Field(ge=0,le=2)
@router.get('/api/v1/commerce-marks/options')
def options():
    try:
        import json
        migrate_legacy_catalog(shipments_repo._database,LOGISTICS_CONFIG_PATH)
        configured=load_catalog(shipments_repo._database)
        entries={m['id']:m for m in configured}
        with shipments_repo._database.lock:
            rows=shipments_repo._database.conn.execute("SELECT DISTINCT mark_id,remote_name,remote_color FROM shipment_marks").fetchall()
        by_name={m['name']:m['id'] for m in configured}
        for row in rows:
            mark={'id':row[0] or by_name.get(row[1]) or 'name:'+row[1],'name':row[1],'color':row[2]}
            if mark['id'].startswith('name:') and mark['name'] in by_name: continue
            entries.setdefault(mark['id'],mark)
        return {'items':configured,'filterItems':list(entries.values())}
    except ValueError as exc: raise HTTPException(400,str(exc)) from None
@router.post('/api/v1/commerce-marks')
def update(body:MarksIn, task_id: str = Header(default="",alias="X-Youzi-Task-Id")):
    try: return apply_marks(shipments_repo,LOGISTICS_CONFIG_PATH,body.ids,body.markIds,body.type,task_id=task_id)
    except ValueError as exc: raise HTTPException(400,str(exc)) from None


@router.post('/api/v1/commerce-marks/sync')
def sync_catalog():
    from ..services.commerce_marks import sync_mark_catalog
    try: return sync_mark_catalog(shipments_repo._database,LOGISTICS_CONFIG_PATH)
    except ValueError as exc: raise HTTPException(400,str(exc)) from None
