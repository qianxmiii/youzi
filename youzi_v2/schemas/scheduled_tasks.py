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
