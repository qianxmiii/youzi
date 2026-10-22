"""运单 API 请求体。"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

SHIPMENT_PAYMENT_STATUSES = frozenset({"UNPAID", "PAID"})


class ShipmentRecordIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    shipment_no: str = Field(
        ...,
        validation_alias=AliasChoices("shipmentNo", "shipment_no"),
        description="运单号",
    )
    customer: str | None = None
    customer_no: str | None = Field(
        default=None, validation_alias=AliasChoices("customerNo", "customer_no")
    )
    channel_code: str | None = Field(
        default=None, validation_alias=AliasChoices("channelCode", "channel_code")
    )
    country_code: str | None = Field(
        default=None, validation_alias=AliasChoices("countryCode", "country_code")
    )
    address_type: str | None = Field(
        default=None, validation_alias=AliasChoices("addressType", "address_type")
    )
    address_code: str | None = Field(
        default=None, validation_alias=AliasChoices("addressCode", "address_code")
    )
    delivery_address: str | None = Field(
        default=None, validation_alias=AliasChoices("deliveryAddress", "delivery_address")
    )
    ctns: int | None = Field(
        default=None, validation_alias=AliasChoices("ctns", "pieceCount", "piece_count")
    )
    charged_weight: float | None = Field(
        default=None,
        validation_alias=AliasChoices("chargedWeight", "charged_weight"),
    )
    zipcode: str | None = None
    product_name: str | None = Field(
        default=None, validation_alias=AliasChoices("productName", "product_name")
    )
    origin_warehouse_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("originWarehouseCode", "origin_warehouse_code"),
    )
    supplier_name: str | None = Field(
        default=None, validation_alias=AliasChoices("supplierName", "supplier_name")
    )
    carrier_code: str | None = Field(
        default=None, validation_alias=AliasChoices("carrierCode", "carrier_code")
    )
    carrier_id: str | None = Field(
        default=None, validation_alias=AliasChoices("carrierId", "carrier_id")
    )
    waybill_id: str | None = Field(
        default=None, validation_alias=AliasChoices("waybillId", "waybill_id")
    )
    tracking_number: str | None = Field(
        default=None, validation_alias=AliasChoices("trackingNumber", "tracking_number")
    )
    express_code: str | None = Field(
        default=None, validation_alias=AliasChoices("expressCode", "express_code")
    )
    customer_shipment_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("customerShipmentId", "customer_shipment_id"),
    )
    amazon_ref_id: str | None = Field(
        default=None, validation_alias=AliasChoices("amazonRefId", "amazon_ref_id")
    )
    bill_of_lading_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("billOfLadingNo", "bill_of_lading_no"),
    )
    container_no: str | None = Field(
        default=None, validation_alias=AliasChoices("containerNo", "container_no"),
    )
    vessel_name: str | None = Field(
        default=None, validation_alias=AliasChoices("vesselName", "vessel_name")
    )
    voyage_no: str | None = Field(
        default=None, validation_alias=AliasChoices("voyageNo", "voyage_no")
    )
    vessel_voyage: str | None = Field(
        default=None, validation_alias=AliasChoices("vesselVoyage", "vessel_voyage")
    )
    etd: str | None = None
    eta: str | None = None
    atd: str | None = None
    ata: str | None = None
    origin_port_code: str | None = Field(
        default=None, validation_alias=AliasChoices("originPortCode", "origin_port_code")
    )
    destination_port_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("destinationPortCode", "destination_port_code"),
    )
    expected_delivery_time: str | None = Field(
        default=None,
        validation_alias=AliasChoices("expectedDeliveryTime", "expected_delivery_time"),
    )
    warehouse_entry_time: str | None = Field(
        default=None,
        validation_alias=AliasChoices("warehouseEntryTime", "warehouse_entry_time"),
    )
    delivered_time: str | None = Field(
        default=None, validation_alias=AliasChoices("deliveredTime", "delivered_time")
    )
    status_code: str | None = Field(
        default="0", validation_alias=AliasChoices("statusCode", "status_code")
    )
    route_status: str | None = Field(
        default=None, validation_alias=AliasChoices("routeStatus", "route_status")
    )
    payment_status: str | None = Field(
        default=None, validation_alias=AliasChoices("paymentStatus", "payment_status")
    )

    @field_validator("payment_status")
    @classmethod
    def _payment_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        text = v.strip().upper()
        if not text:
            return None
        if text not in SHIPMENT_PAYMENT_STATUSES:
            raise ValueError("paymentStatus 须为 UNPAID 或 PAID")
        return text


class ShipmentUpdateIn(BaseModel):
    """更新运单：运单号不可改。"""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    customer: str | None = None
    customer_no: str | None = Field(
        default=None, validation_alias=AliasChoices("customerNo", "customer_no")
    )
    channel_code: str | None = Field(
        default=None, validation_alias=AliasChoices("channelCode", "channel_code")
    )
    country_code: str | None = Field(
        default=None, validation_alias=AliasChoices("countryCode", "country_code")
    )
    address_type: str | None = Field(
        default=None, validation_alias=AliasChoices("addressType", "address_type")
    )
    address_code: str | None = Field(
        default=None, validation_alias=AliasChoices("addressCode", "address_code")
    )
    delivery_address: str | None = Field(
        default=None, validation_alias=AliasChoices("deliveryAddress", "delivery_address")
    )
    ctns: int | None = Field(
        default=None, validation_alias=AliasChoices("ctns", "pieceCount", "piece_count")
    )
    charged_weight: float | None = Field(
        default=None,
        validation_alias=AliasChoices("chargedWeight", "charged_weight"),
    )
    zipcode: str | None = None
    product_name: str | None = Field(
        default=None, validation_alias=AliasChoices("productName", "product_name")
    )
    origin_warehouse_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("originWarehouseCode", "origin_warehouse_code"),
    )
    supplier_name: str | None = Field(
        default=None, validation_alias=AliasChoices("supplierName", "supplier_name")
    )
    carrier_code: str | None = Field(
        default=None, validation_alias=AliasChoices("carrierCode", "carrier_code")
    )
    carrier_id: str | None = Field(
        default=None, validation_alias=AliasChoices("carrierId", "carrier_id")
    )
    waybill_id: str | None = Field(
        default=None, validation_alias=AliasChoices("waybillId", "waybill_id")
    )
    tracking_number: str | None = Field(
        default=None, validation_alias=AliasChoices("trackingNumber", "tracking_number")
    )
    express_code: str | None = Field(
        default=None, validation_alias=AliasChoices("expressCode", "express_code")
    )
    customer_shipment_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("customerShipmentId", "customer_shipment_id"),
    )
    amazon_ref_id: str | None = Field(
        default=None, validation_alias=AliasChoices("amazonRefId", "amazon_ref_id")
    )
    bill_of_lading_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("billOfLadingNo", "bill_of_lading_no"),
    )
    container_no: str | None = Field(
        default=None, validation_alias=AliasChoices("containerNo", "container_no"),
    )
    vessel_name: str | None = Field(
        default=None, validation_alias=AliasChoices("vesselName", "vessel_name")
    )
    voyage_no: str | None = Field(
        default=None, validation_alias=AliasChoices("voyageNo", "voyage_no")
    )
    vessel_voyage: str | None = Field(
        default=None, validation_alias=AliasChoices("vesselVoyage", "vessel_voyage")
    )
    etd: str | None = None
    eta: str | None = None
    atd: str | None = None
    ata: str | None = None
    origin_port_code: str | None = Field(
        default=None, validation_alias=AliasChoices("originPortCode", "origin_port_code")
    )
    destination_port_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("destinationPortCode", "destination_port_code"),
    )
    expected_delivery_time: str | None = Field(
        default=None,
        validation_alias=AliasChoices("expectedDeliveryTime", "expected_delivery_time"),
    )
    warehouse_entry_time: str | None = Field(
        default=None,
        validation_alias=AliasChoices("warehouseEntryTime", "warehouse_entry_time"),
    )
    delivered_time: str | None = Field(
        default=None, validation_alias=AliasChoices("deliveredTime", "delivered_time")
    )
    status_code: str | None = Field(
        default=None, validation_alias=AliasChoices("statusCode", "status_code")
    )
    route_status: str | None = Field(
        default=None, validation_alias=AliasChoices("routeStatus", "route_status")
    )
    payment_status: str | None = Field(
        default=None, validation_alias=AliasChoices("paymentStatus", "payment_status")
    )

    @field_validator("payment_status")
    @classmethod
    def _payment_status_update(cls, v: str | None) -> str | None:
        if v is None:
            return None
        text = v.strip().upper()
        if not text:
            return None
        if text not in SHIPMENT_PAYMENT_STATUSES:
            raise ValueError("paymentStatus 须为 UNPAID 或 PAID")
        return text

    amz_push_dest_port: str | None = Field(
        default=None,
        validation_alias=AliasChoices("amzPushDestPort", "amz_push_dest_port"),
    )
    amz_push_origin_port: str | None = Field(
        default=None,
        validation_alias=AliasChoices("amzPushOriginPort", "amz_push_origin_port"),
    )
    push_amz_update: bool = Field(
        default=False,
        validation_alias=AliasChoices("pushAmzUpdate", "push_amz_update"),
    )

    def to_payload(self) -> dict[str, Any]:
        out = self.model_dump(exclude_none=True, exclude={"push_amz_update"})
        for name in ("carrier_id", "tracking_number"):
            if name in self.model_fields_set and getattr(self, name) is None:
                out[name] = None
        return out


class ShipmentBatchIdsIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("ids", "shipmentIds"),
    )


class DpsExportJobCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    export_type: str = Field(
        ...,
        validation_alias=AliasChoices("exportType", "export_type"),
        description="cargo|mark|markSplit|markRename|packinglist|warehouseform|warehouseEntry|warehouseEntryPdf",
    )
    ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("ids", "shipmentIds"),
    )
    split_spec: str | None = Field(
        default=None,
        validation_alias=AliasChoices("splitSpec", "split_spec"),
    )
    rename_fields: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("renameFields", "rename_fields"),
        description="唛头（重命名）字段顺序，如 shipmentNo, addressCode, ctns",
    )
    rename_separator: str | None = Field(
        default=None,
        validation_alias=AliasChoices("renameSeparator", "rename_separator"),
        description="唛头（重命名）分隔符，如 -",
    )
    rename_folder: str | None = Field(
        default=None,
        validation_alias=AliasChoices("renameFolder", "rename_folder"),
        description="唛头（重命名）文件夹字段；相同值放入同一目录，如 customerNo",
    )
    rename_country_lang: str | None = Field(
        default=None,
        validation_alias=AliasChoices("renameCountryLang", "rename_country_lang"),
        description="唛头（重命名）国家字段语言：en（默认国家码缩写如 AU）或 zh（中文名）",
    )


class ShipmentMarkSplitDownloadIn(BaseModel):
    """单票唛头拆分：segments 为各工厂件数，如 [1, 2, 2]。"""

    model_config = ConfigDict(populate_by_name=True)

    ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=1,
        validation_alias=AliasChoices("ids", "shipmentIds"),
    )
    segments: list[int] | None = Field(default=None, min_length=1, max_length=100)
    split_spec: str | None = Field(
        default=None,
        validation_alias=AliasChoices("splitSpec", "split_spec"),
        description="空格/逗号分隔件数，如 1 2 2",
    )

    @field_validator("segments")
    @classmethod
    def _segments_positive(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return None
        for n in v:
            if n <= 0:
                raise ValueError("拆分件数须为正整数")
        return v

    def resolved_segments(self) -> list[int]:
        from ..services.mark_pdf_split import parse_mark_split_segments

        if self.segments:
            return parse_mark_split_segments(self.segments)
        if self.split_spec and self.split_spec.strip():
            return parse_mark_split_segments(self.split_spec)
        raise ValueError("请提供 segments 或 splitSpec（如 1 2 2）")


class ShipmentBatchUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("ids", "shipmentIds"),
    )
    updates: ShipmentUpdateIn


class ShipmentBatchItemError(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = ""
    shipment_no: str = Field(default="", alias="shipmentNo")
    message: str = ""


class ShipmentSubscribeBatchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total: int = 0
    subscribed: int = 0
    failed: int = 0
    errors: list[dict[str, str]] = Field(default_factory=list)


class ShipmentUnsubscribeBatchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total: int = 0
    unsubscribed: int = 0


class ShipmentBatchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: list[ShipmentBatchItemError] = Field(default_factory=list)
    errors: list[ShipmentBatchItemError] = Field(default_factory=list)


class ShipmentDpsSyncByOrderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_nos: list[str] = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("shipmentNos", "shipment_nos"),
    )


class ShipmentDpsRouteStatusSyncRequest(BaseModel):
    """明细状态同步：shipmentNos 为空则同步全部有 waybillId 的运单。"""

    model_config = ConfigDict(populate_by_name=True)

    shipment_nos: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("shipmentNos", "shipment_nos"),
    )


class ShipmentDpsSyncByOrderResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    skipped: bool = False
    reason: str | None = None
    error: str | None = None
    remote_total: int = Field(default=0, alias="remoteTotal")
    total: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0
    not_found: int = Field(default=0, alias="notFound")
    not_found_nos: list[str] = Field(default_factory=list, alias="notFoundNos")
    pages: int = 0
    errors: list[str] = Field(default_factory=list)


class ShipmentDpsRouteStatusSyncResult(BaseModel):
    """按 waybillId 拉取明细状态轨迹并回写。"""

    model_config = ConfigDict(populate_by_name=True)

    total: int = 0
    updated: int = 0
    unchanged: int = 0
    empty: int = 0
    failed: int = 0
    not_local: int = Field(default=0, alias="notLocal")
    missing_waybill_id: int = Field(default=0, alias="missingWaybillId")
    missing_waybill_id_nos: list[str] = Field(
        default_factory=list, alias="missingWaybillIdNos"
    )
    customs_exception_opened: int = Field(default=0, alias="customsExceptionOpened")
    customs_exception_closed: int = Field(default=0, alias="customsExceptionClosed")
    errors: list[str] = Field(default_factory=list)
