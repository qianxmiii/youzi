"""运单复制文案（与 frontend/src/utils/shipmentCopyFormat.ts 对齐）。"""

from __future__ import annotations

from typing import Any

from ..last_mile_tracking import (
    express_code_to_carrier_hint,
    infer_last_mile_carrier_hint,
    normalize_last_mile_tracking_number,
)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return s.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def join_equals_parts(parts: list[Any]) -> str:
    """用 ` = ` 连接非空片段；空值不产生多余等号。"""
    return " = ".join(p for p in (_cell(x) for x in parts) if p)


def _format_ctns_for_copy(ctns: Any) -> str:
    if ctns is None:
        return ""
    return f"{ctns}ctns"


def _zip_for_copy(value: Any) -> str:
    zipcode = _cell(value)
    if zipcode == "0000":
        return ""
    return zipcode


def _warehouse_or_zip_for_copy(row: dict[str, Any]) -> str:
    warehouse = _cell(row.get("addressCode"))
    if warehouse:
        return warehouse
    return _zip_for_copy(row.get("zipcode"))


def _norm_copy_key(value: str) -> str:
    return value.strip().upper()


def shipment_detail_identifier_parts_for_copy(row: dict[str, Any]) -> list[str]:
    """关联单号、客户编号、货件号；关联单号与货件号相同（忽略大小写）只保留一处。"""
    ref = _cell(row.get("refShipmentNo"))
    customer_no = _cell(row.get("customerNo"))
    shipment_id = _cell(row.get("customerShipmentId"))
    ref_same_as_shipment = (
        bool(ref and shipment_id) and _norm_copy_key(ref) == _norm_copy_key(shipment_id)
    )
    parts: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        if not value:
            return
        key = _norm_copy_key(value)
        if key in seen:
            return
        seen.add(key)
        parts.append(value)

    add(ref)
    add(customer_no)
    if not ref_same_as_shipment:
        add(shipment_id)
    return parts


def format_shipment_detail_summary_line(row: dict[str, Any]) -> str:
    """单行：运单号 = [关联单号] [= 客户编号] [= 货件号] = 仓库（空则邮编，0000 省略）= Nctns。"""
    return join_equals_parts(
        [
            row.get("shipmentNo"),
            *shipment_detail_identifier_parts_for_copy(row),
            _warehouse_or_zip_for_copy(row),
            _format_ctns_for_copy(row.get("ctns")),
        ]
    )


def format_shipment_detail_summary_copy_text(rows: list[dict[str, Any]]) -> str:
    """多行运单明细摘要（不含转单号），运单之间只换行。"""
    if not rows:
        return ""
    return "\n".join(format_shipment_detail_summary_line(row) for row in rows)


_COPY_CARRIER_LABELS = {
    "ups": "UPS",
    "fedex": "FedEx",
    "usps": "USPS",
    "dhl": "DHL",
    "conwest": "Conwest",
    "dpd": "DPD UK",
}


def format_shipment_tracking_number_suffix_line(row: dict[str, Any]) -> str:
    """转单号行：`-- FedEx 876457312498`；无转单号时返回空。"""
    number, parsed_hint = normalize_last_mile_tracking_number(row.get("trackingNumber"))
    number = (number or "").strip()
    if not number:
        return ""
    hint = (
        express_code_to_carrier_hint(row.get("expressCode"))
        or infer_last_mile_carrier_hint(number)
        or parsed_hint
    )
    label = _COPY_CARRIER_LABELS.get(hint or "", "尾程")
    return f"-- {label} {number}"


def format_shipment_tracking_numbers_copy_text(rows: list[dict[str, Any]]) -> str:
    """复制转单号：明细行 + 可选第二行承运商转单号，运单之间空一行。"""
    if not rows:
        return ""
    blocks: list[str] = []
    for row in rows:
        head = format_shipment_detail_summary_line(row)
        suffix = format_shipment_tracking_number_suffix_line(row)
        blocks.append(f"{head}\n{suffix}" if suffix else head)
    return "\n\n".join(blocks)
