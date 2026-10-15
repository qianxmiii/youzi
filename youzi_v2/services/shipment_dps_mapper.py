"""DPS customPageSalesAssistant 行 → 本地 shipments 字段映射。"""

from __future__ import annotations

from typing import Any

from ..db.shipment_route_status import map_dps_route_status


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _opt_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _infer_platform_warehouse_type(
    customer_no: str | None,
    address_code: str | None,
    customer_shipment_id: str | None = None,
) -> str:
    """deliveryAddressType=0 时在 AMZ / WFS 间区分。"""
    blob = " ".join(
        x
        for x in (customer_no or "", address_code or "", customer_shipment_id or "")
        if x
    ).upper()
    if "WFS" in blob:
        return "WFS"
    return "AMZ"


def map_dps_address_type(
    delivery_address_type: Any,
    *,
    customer_no: str | None = None,
    address_code: str | None = None,
    customer_shipment_id: str | None = None,
) -> str | None:
    """
    DPS deliveryAddressType：0=平台仓(AMZ/WFS)，2=私人地址(3PL)。
    0 时按货件号/仓库代码含 WFS 判 WFS，否则 AMZ。
    """
    raw = _opt_str(delivery_address_type)
    if raw is None:
        return None
    if raw == "2":
        return "3PL"
    if raw == "0":
        return _infer_platform_warehouse_type(
            customer_no, address_code, customer_shipment_id
        )
    return None


def map_dps_payment_status(value: Any) -> str | None:
    """DPS clientVerifyStatus：0=未付款，1=已付款。"""
    if value is None or str(value).strip() == "":
        return None
    try:
        n = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    if n == 1:
        return "PAID"
    if n == 0:
        return "UNPAID"
    return None


def map_dps_status(
    row: dict[str, Any],
    route: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> str:
    """
    粗状态：仅 signingTime → DELIVERED；有轨迹 status 则 IN_TRANSIT；否则 UNKNOWN。
    不读 markVos / 601 / nodeDesc（601 只写入明细状态 route_status=TRACK_SIGNED）。
    """
    del params  # 保留签名兼容；粗状态不再使用 markVos
    if _opt_str(row.get("signingTime")):
        return "DELIVERED"
    if _opt_str(route.get("status")):
        return "IN_TRANSIT"
    return "UNKNOWN"


def dps_row_to_shipment(row: dict[str, Any]) -> dict[str, Any] | None:
    """将 DPS rows[] 单项转为 upsert_by_shipment_no 可用的 snake_case 字典。"""
    shipment_no = _opt_str(row.get("odd"))
    if not shipment_no:
        return None

    params = row.get("params") if isinstance(row.get("params"), dict) else {}
    route = (
        params.get("commerceWaybillRouteInfo")
        if isinstance(params.get("commerceWaybillRouteInfo"), dict)
        else {}
    )
    country_vo = (
        params.get("countryVo") if isinstance(params.get("countryVo"), dict) else {}
    )

    customer_no = _opt_str(row.get("internalOrderNum")) or ""
    ref_shipment_no = _opt_str(row.get("assOrderNumber")) or ""
    customer_shipment_id = _opt_str(params.get("amazonID"))
    address_code = _opt_str(row.get("deliveryWarehouseCode"))
    route_status = map_dps_route_status(route.get("status"))
    payload: dict[str, Any] = {
        "shipment_no": shipment_no,
        "waybill_id": _opt_str(row.get("id")),
        "customer": _opt_str(row.get("clientUserNickName")),
        "customer_no": customer_no,
        "ref_shipment_no": ref_shipment_no,
        "channel_code": _opt_str(row.get("channelCode")),
        "country_code": _opt_str(country_vo.get("enAbbreviation")),
        "address_code": address_code,
        "zipcode": _opt_str(row.get("deliveryZip")),
        "ctns": _opt_int(row.get("totalCtns")) or _opt_int(params.get("ctnsTotal")),
        "product_name": _opt_str(params.get("productName")),
        "origin_warehouse_code": _opt_str(row.get("receiveWarehouseName")),
        "supplier_name": _opt_str(row.get("shipperCompanyName")),
        "carrier_code": _opt_str(row.get("carrierId")),
        "tracking_number": _opt_str(row.get("endOrderNumber"))
        or _opt_str(row.get("carrierNumber")),
        "customer_shipment_id": customer_shipment_id,
        "amazon_ref_id": _opt_str(params.get("amazonReferenceID")),
        "bill_of_lading_no": _opt_str(params.get("ladingBillNum")),
        "expected_delivery_time": _opt_str(route.get("estimatedDeliveryDate")),
        "delivered_time": _opt_str(row.get("signingTime")),
        "latest_tracking_time": _opt_str(route.get("nodeTime"))
        or _opt_str(row.get("warehouseEntryTime")),
        "latest_tracking_desc": _opt_str(route.get("nodeDesc")),
        "status_code": map_dps_status(row, route, params),
        "route_status": route_status,
        "payment_status": map_dps_payment_status(row.get("clientVerifyStatus")),
        "address_type": map_dps_address_type(
            row.get("deliveryAddressType"),
            customer_no=customer_no,
            address_code=address_code,
            customer_shipment_id=customer_shipment_id,
        ),
    }
    return {
        k: v
        for k, v in payload.items()
        if v is not None or k in ("shipment_no", "customer_no", "ref_shipment_no")
    }
