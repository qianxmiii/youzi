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
