from pydantic import BaseModel, ConfigDict, Field


class ScheduledTaskConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    internal_enabled: bool = Field(alias="internalEnabled")
    internal_interval_hours: float = Field(alias="internalIntervalHours")
    carrier_enabled: bool = Field(alias="carrierEnabled")
    carrier_interval_hours: float = Field(alias="carrierIntervalHours")
    initial_delay_sec: float = Field(alias="initialDelaySec")
    last_internal_finished: str | None = Field(default=None, alias="lastInternalFinished")
    last_carrier_finished: str | None = Field(default=None, alias="lastCarrierFinished")
    group_auto_archive_enabled: bool = Field(default=False, alias="groupAutoArchiveEnabled")
    group_auto_archive_last_finished: str | None = Field(
        default=None, alias="groupAutoArchiveLastFinished"
    )
    zipcode_backfill_enabled: bool = Field(default=False, alias="zipcodeBackfillEnabled")
    zipcode_backfill_last_finished: str | None = Field(
        default=None, alias="zipcodeBackfillLastFinished"
    )
    dps_shipment_sync_enabled: bool = Field(default=False, alias="dpsShipmentSyncEnabled")
    dps_shipment_sync_transit_time_start: str | None = Field(
        default=None, alias="dpsShipmentSyncTransitTimeStart"
    )
    dps_shipment_sync_transit_time_end: str | None = Field(
        default=None, alias="dpsShipmentSyncTransitTimeEnd"
    )
    dps_shipment_sync_transit_time_start_default: str | None = Field(
        default=None, alias="dpsShipmentSyncTransitTimeStartDefault"
    )
    dps_shipment_sync_transit_time_end_default: str | None = Field(
        default=None, alias="dpsShipmentSyncTransitTimeEndDefault"
    )
    dps_shipment_sync_transit_time_start_effective: str | None = Field(
        default=None, alias="dpsShipmentSyncTransitTimeStartEffective"
    )
    dps_shipment_sync_transit_time_end_effective: str | None = Field(
        default=None, alias="dpsShipmentSyncTransitTimeEndEffective"
    )
    dps_shipment_sync_last_finished: str | None = Field(
        default=None, alias="dpsShipmentSyncLastFinished"
    )
    exception_followup_enabled: bool = Field(default=False, alias="exceptionFollowupEnabled")
    exception_followup_last_finished: str | None = Field(
        default=None, alias="exceptionFollowupLastFinished"
    )
    sla_scan_enabled: bool = Field(default=True, alias="slaScanEnabled")
    sla_scan_last_finished: str | None = Field(default=None, alias="slaScanLastFinished")
    scheduler_active: bool = Field(alias="schedulerActive")
    script_path: str | None = Field(default=None, alias="scriptPath")
    poll_interval_sec: float | None = Field(default=None, alias="pollIntervalSec")


class ScheduledSyncSettingsUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    internal_enabled: bool = Field(alias="internalEnabled")
    internal_interval_hours: float = Field(
        alias="internalIntervalHours", ge=0.25, le=168
    )
    carrier_enabled: bool = Field(alias="carrierEnabled")
    carrier_interval_hours: float = Field(
        alias="carrierIntervalHours", ge=0.25, le=168
    )
    initial_delay_sec: float = Field(alias="initialDelaySec", ge=0, le=86400)
    group_auto_archive_enabled: bool | None = Field(
        default=None, alias="groupAutoArchiveEnabled"
    )
    zipcode_backfill_enabled: bool | None = Field(
        default=None, alias="zipcodeBackfillEnabled"
    )
    dps_shipment_sync_enabled: bool | None = Field(
        default=None, alias="dpsShipmentSyncEnabled"
    )
    dps_shipment_sync_transit_time_start: str | None = Field(
        default=None, alias="dpsShipmentSyncTransitTimeStart"
    )
    dps_shipment_sync_transit_time_end: str | None = Field(
        default=None, alias="dpsShipmentSyncTransitTimeEnd"
    )
    exception_followup_enabled: bool | None = Field(
        default=None, alias="exceptionFollowupEnabled"
    )
    sla_scan_enabled: bool | None = Field(default=None, alias="slaScanEnabled")


class ExceptionFollowupRunResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skipped: bool = False
    reason: str | None = None
    scanned: int = 0
    created: int = 0


class GroupAutoArchiveRunResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skipped: bool = False
    reason: str | None = None
    total: int = 0
    archived: int = 0
    group_ids: list[str] = Field(default_factory=list, alias="groupIds")


class ZipcodeBackfillRunResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skipped: bool = False
    reason: str | None = None
    total: int = 0
    updated: int = 0
    unmatched: int = 0


class ShipmentDpsSyncRunRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    transit_time_start: str | None = Field(default=None, alias="transitTimeStart")
    transit_time_end: str | None = Field(default=None, alias="transitTimeEnd")


class ShipmentDpsSyncRunResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skipped: bool = False
    reason: str | None = None
    error: str | None = None
    transit_time_start: str | None = Field(default=None, alias="transitTimeStart")
    transit_time_end: str | None = Field(default=None, alias="transitTimeEnd")
    remote_total: int = Field(default=0, alias="remoteTotal")
    total: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0
    pages: int = 0
    errors: list[str] = Field(default_factory=list)


class ScheduledTaskOverview(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    config: ScheduledTaskConfig
    internal_today: dict = Field(alias="internalToday")
    carrier_today: dict = Field(alias="carrierToday")
    tasks: list[dict] = Field(default_factory=list)


class TrackingSyncJobRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    source: str
    trigger_type: str = Field(alias="triggerType")
    status: str
    total_shipments: int = Field(alias="totalShipments")
    updated_shipments: int = Field(alias="updatedShipments")
    new_log_count: int = Field(alias="newLogCount")
    skipped: int
    empty_count: int = Field(alias="emptyCount")
    not_found: int = Field(alias="notFound")
    error_count: int = Field(alias="errorCount")
    errors: list[str] = Field(default_factory=list)
    started_time: str = Field(alias="startedTime")
    finished_time: str | None = Field(default=None, alias="finishedTime")


class TrackingSyncJobListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[TrackingSyncJobRecord]
    total: int
    limit: int
    offset: int


class ScheduledSyncRunResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skipped: bool = False
    reason: str | None = None
    internal: dict | None = None
    carrier: dict | None = None
