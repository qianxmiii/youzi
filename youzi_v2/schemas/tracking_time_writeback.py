"""轨迹时间回写 API 模型。"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TrackingTimeReviewIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    action: str = Field(
        ...,
        description="use_expected_delivery | use_signed_track | manual | reject",
    )
    manual_value: str | None = Field(
        default=None,
        validation_alias=AliasChoices("manualValue", "manual_value"),
    )


class TrackingTimeBatchReviewIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ids: list[str] = Field(..., min_length=1, max_length=200)
    action: str = Field(
        ...,
        description="use_expected_delivery | use_signed_track | reject",
    )
