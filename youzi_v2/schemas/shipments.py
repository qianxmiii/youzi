"""运单 API 请求体。"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


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
    delivered_time: str | None = Field(
        default=None, validation_alias=AliasChoices("deliveredTime", "delivered_time")
    )
    status_code: str | None = Field(
        default="UNKNOWN", validation_alias=AliasChoices("statusCode", "status_code")
    )


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
    delivered_time: str | None = Field(
        default=None, validation_alias=AliasChoices("deliveredTime", "delivered_time")
    )
    status_code: str | None = Field(
        default=None, validation_alias=AliasChoices("statusCode", "status_code")
    )

    def to_payload(self) -> dict[str, Any]:
        out = self.model_dump(exclude_none=True)
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
