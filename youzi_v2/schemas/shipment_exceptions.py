"""运单异常事件 API 请求体。"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ShipmentExceptionOpenIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_nos: list[str] = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("shipmentNos", "shipment_nos"),
    )
    exception_code: str = Field(
        ...,
        validation_alias=AliasChoices("exceptionCode", "exception_code"),
    )
    note: str | None = None
    opened_time: str | None = Field(
        default=None,
        validation_alias=AliasChoices("openedTime", "opened_time"),
        description="异常开始时间 YYYY-MM-DD HH:mm:ss，默认当前时间",
    )


class ShipmentExceptionCloseIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_nos: list[str] = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("shipmentNos", "shipment_nos"),
    )
    note: str | None = None
    closed_time: str | None = Field(
        default=None,
        validation_alias=AliasChoices("closedTime", "closed_time"),
        description="异常结束时间 YYYY-MM-DD HH:mm:ss，默认当前时间",
    )
