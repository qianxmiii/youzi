from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ShipmentPerformanceQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date_from: str | None = Field(default=None, alias="dateFrom")
    date_to: str | None = Field(default=None, alias="dateTo")
    date_basis: str = Field(default="atd", alias="dateBasis")
    channel_code: str | None = Field(default=None, alias="channelCode")
    carrier_code: str | None = Field(default=None, alias="carrierCode")
    customer: str | None = None
    destination_port_code: str | None = Field(default=None, alias="destinationPortCode")


class PerformanceMetricBlock(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    avg_days: float | None = Field(default=None, alias="avgDays")
    sample_count: int = Field(default=0, alias="sampleCount")
    p50_days: float | None = Field(default=None, alias="p50Days")
    p90_days: float | None = Field(default=None, alias="p90Days")
    min_days: float | None = Field(default=None, alias="minDays")
    max_days: float | None = Field(default=None, alias="maxDays")


class ShipmentPerformanceOverviewKpi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_count: int = Field(alias="totalCount")
    signed_count: int = Field(alias="signedCount")
    signed_rate: float = Field(alias="signedRate")
    anomaly_count: int = Field(alias="anomalyCount")
    anomaly_rate: float = Field(alias="anomalyRate")
    sea_transit: PerformanceMetricBlock = Field(alias="seaTransit")
    post_arrival: PerformanceMetricBlock = Field(alias="postArrival")
    full_transit: PerformanceMetricBlock = Field(alias="fullTransit")
    delivery_deviation: PerformanceMetricBlock = Field(alias="deliveryDeviation")
    fastest_signed_transit_days: float | None = Field(default=None, alias="fastestSignedTransitDays")
    fastest_signed_shipment_no: str | None = Field(default=None, alias="fastestSignedShipmentNo")
    slowest_signed_transit_days: float | None = Field(default=None, alias="slowestSignedTransitDays")
    slowest_signed_shipment_no: str | None = Field(default=None, alias="slowestSignedShipmentNo")
    channel_ranking: list["PerformanceGroupRow"] = Field(default_factory=list, alias="channelRanking")
    carrier_ranking: list["PerformanceGroupRow"] = Field(default_factory=list, alias="carrierRanking")


class PerformanceGroupRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    total_count: int = Field(alias="totalCount")
    signed_count: int = Field(alias="signedCount")
    signed_rate: float = Field(alias="signedRate")
    sea_transit: PerformanceMetricBlock = Field(alias="seaTransit")
    post_arrival: PerformanceMetricBlock = Field(alias="postArrival")
    full_transit: PerformanceMetricBlock = Field(alias="fullTransit")
    delivery_deviation: PerformanceMetricBlock = Field(alias="deliveryDeviation")
    anomaly_count: int = Field(alias="anomalyCount")
    anomaly_rate: float = Field(alias="anomalyRate")
    fastest_shipment_no: str | None = Field(default=None, alias="fastestShipmentNo")
    slowest_shipment_no: str | None = Field(default=None, alias="slowestShipmentNo")


class PerformanceCarrierChannelRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    carrier_code: str = Field(alias="carrierCode")
    channel_code: str = Field(alias="channelCode")
    total_count: int = Field(alias="totalCount")
    signed_count: int = Field(alias="signedCount")
    sea_transit: PerformanceMetricBlock = Field(alias="seaTransit")
    full_transit: PerformanceMetricBlock = Field(alias="fullTransit")
    anomaly_count: int = Field(alias="anomalyCount")
    anomaly_rate: float = Field(alias="anomalyRate")


class ShipmentPerformanceDetailRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_id: str = Field(alias="shipmentId")
    shipment_no: str = Field(alias="shipmentNo")
    customer: str | None = None
    channel_code: str | None = Field(default=None, alias="channelCode")
    carrier_code: str | None = Field(default=None, alias="carrierCode")
    destination_port_code: str | None = Field(default=None, alias="destinationPortCode")
    etd: str | None = None
    atd: str | None = None
    eta: str | None = None
    ata: str | None = None
    expected_delivery_time: str | None = Field(default=None, alias="expectedDeliveryTime")
    signed_time: str | None = Field(default=None, alias="signedTime")
    departure_deviation_days: int | None = Field(default=None, alias="departureDeviationDays")
    eta_deviation_days: int | None = Field(default=None, alias="etaDeviationDays")
    sea_transit_days: int | None = Field(default=None, alias="seaTransitDays")
    post_arrival_days: int | None = Field(default=None, alias="postArrivalDays")
    full_transit_days: int | None = Field(default=None, alias="fullTransitDays")
    delivery_deviation_days: int | None = Field(default=None, alias="deliveryDeviationDays")
    anomaly_flags: list[str] = Field(default_factory=list, alias="anomalyFlags")


class ShipmentPerformanceAnalysis(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    filters: ShipmentPerformanceQuery
    truncated: bool = False
    analyzed_count: int = Field(alias="analyzedCount")
    overview: ShipmentPerformanceOverviewKpi
    by_channel: list[PerformanceGroupRow] = Field(alias="byChannel")
    by_carrier: list[PerformanceGroupRow] = Field(alias="byCarrier")
    by_carrier_channel: list[PerformanceCarrierChannelRow] = Field(alias="byCarrierChannel")
    by_customer: list[PerformanceGroupRow] = Field(alias="byCustomer")


class ShipmentPerformanceDetailsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ShipmentPerformanceDetailRow]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    truncated: bool = False
