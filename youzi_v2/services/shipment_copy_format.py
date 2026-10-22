"""运单复制文案（与 frontend/src/utils/shipmentCopyFormat.ts 对齐）。"""

from __future__ import annotations

from typing import Any


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


def _warehouse_or_zip_for_copy(row: dict[str, Any]) -> str:
    warehouse = _cell(row.get("addressCode"))
    if warehouse:
        return warehouse
    return _cell(row.get("zipcode"))


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
    """单行：运单号 = [关联单号] [= 客户编号] [= 货件号] = 仓库（空则邮编）= Nctns。"""
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
