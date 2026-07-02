from fastapi import APIRouter

from ..context import *

router = APIRouter()

@router.get("/api/v1/settings/world-clocks")
def get_world_clocks_settings_api():
    """顶栏世界时间全局配置。"""
    return get_world_clocks_settings(_database).to_api_dict()

@router.put("/api/v1/settings/world-clocks")
def update_world_clocks_settings_api(body: WorldClocksSettingsUpdate):
    try:
        saved = save_world_clocks_settings(
            _database,
            enabled=body.enabled,
            use24h=body.use24h,
            zones=[{"tz": z.tz, "label": z.label} for z in body.zones],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return saved.to_api_dict()

@router.get("/api/v1/scheduled-tasks/overview", response_model=ScheduledTaskOverview)
def get_scheduled_tasks_overview():
    settings = get_scheduled_sync_settings(_database)
    return ScheduledTaskOverview(
        config=ScheduledTaskConfig(**build_scheduled_task_config(_database)),
        internalToday=tracking_jobs_repo.today_stats("internal"),
        carrierToday=tracking_jobs_repo.today_stats("carrier"),
        tasks=builtin_scheduled_tasks(settings, _database),
    )

@router.put("/api/v1/scheduled-tasks/settings", response_model=ScheduledTaskConfig)
def update_scheduled_tasks_settings(body: ScheduledSyncSettingsUpdate):
    save_scheduled_sync_settings(
        _database,
        internal_enabled=body.internal_enabled,
        internal_interval_hours=body.internal_interval_hours,
        carrier_enabled=body.carrier_enabled,
        carrier_interval_hours=body.carrier_interval_hours,
        initial_delay_sec=body.initial_delay_sec,
    )
    if body.group_auto_archive_enabled is not None:
        save_group_auto_archive_enabled(
            _database,
            enabled=body.group_auto_archive_enabled,
        )
    if body.zipcode_backfill_enabled is not None:
        save_zipcode_backfill_enabled(
            _database,
            enabled=body.zipcode_backfill_enabled,
        )
    if body.dps_shipment_sync_enabled is not None:
        save_shipment_dps_sync_enabled(
            _database,
            enabled=body.dps_shipment_sync_enabled,
        )
    if (
        body.dps_shipment_sync_transit_time_start is not None
        or body.dps_shipment_sync_transit_time_end is not None
    ):
        save_shipment_dps_sync_transit_time_range(
            _database,
            transit_time_start=body.dps_shipment_sync_transit_time_start,
            transit_time_end=body.dps_shipment_sync_transit_time_end,
        )
    if body.exception_followup_enabled is not None:
        save_exception_followup_enabled(
            _database,
            enabled=body.exception_followup_enabled,
        )
    return ScheduledTaskConfig(**build_scheduled_task_config(_database))

@router.get("/api/v1/scheduled-tasks/jobs", response_model=TrackingSyncJobListResponse)
def list_scheduled_task_jobs(
    source: str | None = Query(None, description="carrier / internal，默认全部"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    src = source.strip().lower() if source else None
    if src and src not in ("internal", "carrier"):
        raise HTTPException(status_code=400, detail="source 须为 internal 或 carrier")
    data = tracking_jobs_repo.list_jobs(source=src, limit=limit, offset=offset)
    return TrackingSyncJobListResponse(**data)

@router.post("/api/v1/scheduled-tasks/run-internal-sync", response_model=ScheduledSyncRunResult)
def run_scheduled_tasks_internal_sync():
    result = run_scheduled_internal_sync(
        shipments_repo,
        internal_tracking_repo,
        tracking_jobs_repo,
        LOGISTICS_CONFIG_PATH,
        force=True,
    )
    return ScheduledSyncRunResult(**result)

@router.post("/api/v1/scheduled-tasks/run-carrier-sync", response_model=ScheduledSyncRunResult)
def run_scheduled_tasks_carrier_sync():
    result = run_scheduled_carrier_sync(
        shipments_repo,
        carrier_tracking_repo,
        tracking_jobs_repo,
        LOGISTICS_CONFIG_PATH,
        force=True,
    )
    return ScheduledSyncRunResult(**result)

@router.post(
    "/api/v1/scheduled-tasks/run-group-auto-archive",
    response_model=GroupAutoArchiveRunResult,
)
def run_scheduled_tasks_group_auto_archive():
    result = run_group_auto_archive_batch(
        shipment_groups_repo,
        force=True,
        trigger="manual",
    )
    return GroupAutoArchiveRunResult(**result)

@router.post(
    "/api/v1/scheduled-tasks/run-zipcode-backfill",
    response_model=ZipcodeBackfillRunResult,
)
def run_scheduled_tasks_zipcode_backfill():
    result = run_zipcode_backfill_batch(
        shipments_repo,
        force=True,
        trigger="manual",
    )
    return ZipcodeBackfillRunResult(**result)

@router.post(
    "/api/v1/scheduled-tasks/run-dps-shipment-sync",
    response_model=ShipmentDpsSyncRunResult,
)
def run_scheduled_tasks_dps_shipment_sync(
    body: ShipmentDpsSyncRunRequest | None = Body(None),
):
    result = run_shipment_dps_sync_batch(
        shipments_repo,
        LOGISTICS_CONFIG_PATH,
        transit_time_start=body.transit_time_start if body else None,
        transit_time_end=body.transit_time_end if body else None,
        force=True,
        trigger="manual",
    )
    return ShipmentDpsSyncRunResult(**result)

@router.post(
    "/api/v1/scheduled-tasks/run-exception-followup",
    response_model=ExceptionFollowupRunResult,
)
def run_scheduled_tasks_exception_followup():
    result = scan_exception_followup_reminders(
        shipment_exception_followup_repo,
        force=True,
        trigger="manual",
    )
    return ExceptionFollowupRunResult(**result)

@router.post("/api/v1/scheduled-tasks/run-tracking-sync", response_model=ScheduledSyncRunResult)
def run_scheduled_tasks_tracking_sync():
    """立即执行内部 + 承运商（忽略间隔，仍受页面开关影响时可 force）。"""
    result = run_scheduled_tracking_sync(
        shipments_repo,
        internal_tracking_repo,
        carrier_tracking_repo,
        tracking_jobs_repo,
        LOGISTICS_CONFIG_PATH,
        force=True,
    )
    return ScheduledSyncRunResult(**result)
