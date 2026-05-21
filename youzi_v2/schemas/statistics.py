from pydantic import BaseModel, Field


class DistributionItem(BaseModel):
    key: str
    label: str
    count: int
    ratio: float = Field(description="0~1，占分母比例")


class TransitBaselineStats(BaseModel):
    available: bool
    sample_count: int = Field(alias="sampleCount")
    avg_days: float | None = Field(default=None, alias="avgDays")
    std_dev_days: float | None = Field(default=None, alias="stdDevDays")
    min_days: int | None = Field(default=None, alias="minDays")
    max_days: int | None = Field(default=None, alias="maxDays")
    description: str = ""

    model_config = {"populate_by_name": True}


class ShipmentStatisticsOverview(BaseModel):
    total: int
    status_distribution: list[DistributionItem] = Field(alias="statusDistribution")
    channel_distribution: list[DistributionItem] = Field(alias="channelDistribution")
    sea_channel_distribution: list[DistributionItem] = Field(
        alias="seaChannelDistribution"
    )
    sea_channel_total: int = Field(alias="seaChannelTotal", description="海运渠道运单数")
    carrier_distribution: list[DistributionItem] = Field(alias="carrierDistribution")
    transit_baseline: TransitBaselineStats = Field(alias="transitBaseline")

    model_config = {"populate_by_name": True}
