"""每日同步入口。凭据只写，响应和历史中不包含授权。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, SecretStr, Field

from ..context import (
    _database, LOGISTICS_CONFIG_PATH, shipments_repo, internal_tracking_repo,
    carrier_tracking_repo, tracking_jobs_repo,
)
from ..services.daily_sync import DailySyncManager
from ..services.shipment_dps_sync import run_shipment_dps_sync_batch
from ..services.tracking_sync import sync_all_tracking
from ..services.carrier_tracking_sync import sync_carrier_tracking
from ..services.shipment_dps_route_status_sync import sync_route_status_by_waybill_ids
from ..services.shipment_dps_sync_settings import get_shipment_dps_sync_settings

router = APIRouter(tags=['daily-sync'])


def _dps(variant):
    return lambda start, end, log: run_shipment_dps_sync_batch(
        shipments_repo, LOGISTICS_CONFIG_PATH, transit_time_start=start, transit_time_end=end,
        force=True, trigger='manual', variant=variant, log=log,
    )


manager = DailySyncManager(_database, LOGISTICS_CONFIG_PATH, {
    'pickup': _dps('pickup'), 'warehoused': _dps('warehoused'), 'transit': _dps('default'),
    'internal': lambda start, end, log: sync_all_tracking(
        shipments_repo, internal_tracking_repo, LOGISTICS_CONFIG_PATH,
        jobs_repo=tracking_jobs_repo, trigger='manual', log=log,
    ),
    'carrier': lambda start, end, log: sync_carrier_tracking(
        shipments_repo, carrier_tracking_repo, tracking_jobs_repo, LOGISTICS_CONFIG_PATH,
        trigger='manual', log=log,
    ),
    'route': lambda start, end, log: sync_route_status_by_waybill_ids(
        shipments_repo, LOGISTICS_CONFIG_PATH, log=log,
    ),
})


class DailySyncStart(BaseModel):
    authorization: SecretStr = SecretStr('')
    resume_id: str | None = Field(None, alias='resumeId', max_length=100)
    start: str | None = Field(None, max_length=30)
    end: str | None = Field(None, max_length=30)


@router.get('/api/v1/daily-sync')
def daily_sync_status():
    return {'configured': manager.configured(), 'run': manager.latest()}


@router.post('/api/v1/daily-sync', status_code=202)
def start_daily_sync(body: DailySyncStart):
    settings = get_shipment_dps_sync_settings(_database)
    start, end = settings.effective_transit_time_range()
    try:
        return manager.start(
            body.authorization.get_secret_value(), resume_id=body.resume_id,
            start=body.start if body.start is not None else start,
            end=body.end if body.end is not None else end,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@router.post('/api/v1/daily-sync/{run_id}/close')
def close_daily_sync(run_id: str):
    try:
        return manager.close(run_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
