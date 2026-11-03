from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChannelSlaRuleIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    estimated_days: int | None = Field(default=None, alias="estimatedDays", ge=1)
    estimated_days_min: int | None = Field(default=None, alias="estimatedDaysMin", ge=1)
    estimated_days_max: int | None = Field(default=None, alias="estimatedDaysMax", ge=1)
    post_arrival_days_min: int = Field(default=7, alias="postArrivalDaysMin", ge=0)
    post_arrival_days_max: int = Field(default=15, alias="postArrivalDaysMax", ge=0)
    dw_early_days: int = Field(default=0, alias="dwEarlyDays", ge=0, le=365)
    dw_late_days: int = Field(default=0, alias="dwLateDays", ge=0, le=365)
    carrier_code: str = Field(default="", alias="carrierCode")
    start_field: str = Field(default="ATD", alias="startField")
    warning_days: int = Field(default=3, alias="warningDays", ge=0)
    severe_overdue_days: int = Field(default=7, alias="severeOverdueDays", ge=0)
    enabled: bool = True
    note: str = ""


    @model_validator(mode='after')
    def validate_range(self):
        if self.post_arrival_days_min > self.post_arrival_days_max:
            raise ValueError("到港后最长天数不能小于最短天数")
        if self.estimated_days_min is None and self.estimated_days_max is None:
            if self.estimated_days is None:
                raise ValueError('请填写时效起止天数')
            self.estimated_days_min = self.estimated_days_max = self.estimated_days
        elif self.estimated_days_min is None or self.estimated_days_max is None:
            raise ValueError('时效最短和最长天数必须同时填写')
        if self.estimated_days_min > self.estimated_days_max:
            raise ValueError('最长天数不能小于最短天数')
        if self.estimated_days is not None and self.estimated_days != self.estimated_days_max:
            raise ValueError('兼容预估天数必须与区间上限一致')
        self.estimated_days = self.estimated_days_max
        return self


class ChannelSlaRuleOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    channel_code: str = Field(alias="channelCode")
    carrier_code: str = Field(alias="carrierCode")
    start_field: str = Field(alias="startField")
    estimated_days: int = Field(alias="estimatedDays")
    estimated_days_min: int = Field(alias="estimatedDaysMin")
    estimated_days_max: int = Field(alias="estimatedDaysMax")
    post_arrival_days_min: int = Field(default=7, alias="postArrivalDaysMin", ge=0)
    post_arrival_days_max: int = Field(default=15, alias="postArrivalDaysMax", ge=0)
    dw_early_days: int = Field(default=0, alias="dwEarlyDays")
    dw_late_days: int = Field(default=0, alias="dwLateDays")
    warning_days: int = Field(alias="warningDays")
    severe_overdue_days: int = Field(alias="severeOverdueDays")
    enabled: bool
    note: str = ""
    created_time: str = Field(alias="createdTime")
    updated_time: str = Field(alias="updatedTime")


class ShipmentSlaAlertConvertIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    exception_code: str = Field(default="TRANSIT_TIMEOUT", alias="exceptionCode")
    note: str = ""


class ShipmentSlaAlertNoteIn(BaseModel):
    note: str = ""


class ShipmentSlaAlertBatchIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ids: list[str] = Field(default_factory=list)


class ShipmentSlaScanResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skipped: bool = False
    reason: str | None = None
    scanned: int = 0
    created: int = 0
    updated: int = 0
    resolved: int = 0
