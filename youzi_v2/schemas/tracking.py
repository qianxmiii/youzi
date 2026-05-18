from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TrackingSyncRequest(BaseModel):
    """不传或空列表表示同步全部运单。"""

    model_config = ConfigDict(populate_by_name=True)

    shipment_nos: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("shipmentNos", "shipment_nos"),
    )


class TrackingLogRecord(BaseModel):
    model_config = {"populate_by_name": True}

    id: str
    shipment_no: str = Field(alias="shipmentNo")
    tracking_time: str = Field(alias="trackingTime")
    tracking_desc: str = Field(alias="trackingDesc")
    created_time: str = Field(alias="createdTime")


class TrackingLogListResponse(BaseModel):
    model_config = {"populate_by_name": True}

    items: list[TrackingLogRecord]
    total: int
    limit: int
    offset: int


class TrackingSyncResult(BaseModel):
    total: int = Field(description="库内运单总数")
    updated: int = Field(description="摘要有变化并已写入的运单数")
    skipped: int = Field(default=0, description="最新轨迹与库内摘要相同，跳过")
    empty: int = Field(description="API 有返回但无 logisticsInfors 的运单数")
    not_found: int = Field(alias="notFound", description="API 响应中未出现的运单数")
    log_count: int = Field(alias="logCount", description="写入的轨迹条数合计")
    errors: list[str] = Field(default_factory=list, description="批次请求错误摘要")
    batch_size: int = Field(default=10, alias="batchSize", description="每批查询运单数")
    batches: int = Field(default=0, description="查询批次数")
    job_id: str | None = Field(default=None, alias="jobId")
    unassigned: int = Field(default=0, description="承运商同步：未匹配 vendor 的单数")

    model_config = {"populate_by_name": True}


class TrackingSyncDailyStats(BaseModel):
    source: str
    updated_shipments: int = Field(alias="updatedShipments")
    new_log_count: int = Field(alias="newLogCount")
    job_count: int = Field(alias="jobCount")
    last_finished: str | None = Field(default=None, alias="lastFinished")

    model_config = {"populate_by_name": True}


class CarrierTrackingLogRecord(BaseModel):
    model_config = {"populate_by_name": True}

    id: str
    shipment_no: str = Field(alias="shipmentNo")
    vendor_name: str = Field(alias="vendorName")
    carrier_code: str = Field(alias="carrierCode")
    tracking_time: str = Field(alias="trackingTime")
    tracking_desc: str = Field(alias="trackingDesc")
    created_time: str = Field(alias="createdTime")
