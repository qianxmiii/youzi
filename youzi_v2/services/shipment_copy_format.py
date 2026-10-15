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


def format_shipment_detail_summary_line(row: dict[str, Any]) -> str:
    """单行：运单号 = 货件号 = 派送仓库（空则邮编）= 件数ctns（缺段跳过）。"""
    return join_equals_parts(
        [
            row.get("shipmentNo"),
            row.get("customerShipmentId"),
            _warehouse_or_zip_for_copy(row),
            _format_ctns_for_copy(row.get("ctns")),
        ]
    )


def format_shipment_detail_summary_copy_text(rows: list[dict[str, Any]]) -> str:
    """多行运单明细摘要（不含转单号），运单之间空一行。"""
    if not rows:
        return ""
    return "\n\n".join(format_shipment_detail_summary_line(row) for row in rows)
