from pydantic import BaseModel, ConfigDict, Field


class TrackingFreshnessBucket(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    today: int = 0
    within3d: int = Field(alias="within3d", description="三日内（含今日），自然日")
    older: int = 0
    none: int = 0


class TrackingFreshnessStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    internal: TrackingFreshnessBucket
    carrier: TrackingFreshnessBucket
    carrier_ahead_of_internal: int = Field(
        0,
        alias="carrierAheadOfInternal",
        description="承运商最新节点新于内部的运单数",
    )
    pending_tracking_time_review: int = Field(
        0,
        alias="pendingTrackingTimeReview",
        description="签收时间待轨迹审批的运单数",
    )
    internal_stale_7d: int = Field(
        0,
        alias="internalStale7d",
        description="转运中且有效内部轨迹 ≥7 天未更新",
    )
    internal_stale_14d: int = Field(
        0,
        alias="internalStale14d",
        description="转运中且有效内部轨迹 ≥14 天未更新",
    )
