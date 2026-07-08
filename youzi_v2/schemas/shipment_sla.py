from pydantic import BaseModel, ConfigDict, Field


class ChannelSlaRuleIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    estimated_days: int = Field(alias="estimatedDays", ge=1)
    carrier_code: str = Field(default="", alias="carrierCode")
    start_field: str = Field(default="ATD", alias="startField")
    warning_days: int = Field(default=3, alias="warningDays", ge=0)
    severe_overdue_days: int = Field(default=7, alias="severeOverdueDays", ge=0)
    enabled: bool = True
    note: str = ""


class ChannelSlaRuleOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    channel_code: str = Field(alias="channelCode")
    carrier_code: str = Field(alias="carrierCode")
    start_field: str = Field(alias="startField")
    estimated_days: int = Field(alias="estimatedDays")
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


class ShipmentSlaScanResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skipped: bool = False
    reason: str | None = None
    scanned: int = 0
    created: int = 0
    updated: int = 0
    resolved: int = 0
