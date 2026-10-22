"""催款列表 Excel 导出。"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook

from ..db.shipment_order_status import (
    LEGACY_DELIVERED,
    LEGACY_INSPECTION,
    LEGACY_IN_TRANSIT,
    LEGACY_UNKNOWN,
    STATUS_CANCELLED,
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_ORDERED,
    STATUS_PICKED_UP,
    STATUS_WAREHOUSE_IN,
)

_STATUS_LABELS: dict[str, str] = {
    STATUS_ORDERED: "已下单",
    STATUS_PICKED_UP: "提货中",
    STATUS_WAREHOUSE_IN: "已入仓",
    STATUS_IN_TRANSIT: "转运中",
    STATUS_DELIVERED: "已签收",
    STATUS_CANCELLED: "已取消",
    LEGACY_IN_TRANSIT: "转运中",
    LEGACY_DELIVERED: "已签收",
    LEGACY_INSPECTION: "查验",
    LEGACY_UNKNOWN: "未知",
}

_EXPORT_COLUMNS: list[tuple[str, str]] = [
    ("shipmentNo", "运单号"),
    ("customerNo", "客户单号"),
    ("refShipmentNo", "关联单号"),
    ("billOfLadingNo", "提单号"),
    ("containerNo", "柜号"),
    ("isFcl", "整柜"),
    ("customer", "客户"),
    ("channelNameZh", "渠道"),
    ("channelCode", "渠道编码"),
    ("statusCode", "状态"),
    ("ata", "ATA"),
    ("deliveredTime", "签收日期"),
    ("latestTrackingTime", "最新轨迹时间"),
    ("latestTrackingDesc", "最新轨迹"),
    ("paymentStatus", "付款状态"),
    ("settlementMethodLabel", "结算方式"),
    ("baseDate", "关键日期"),
    ("dueDate", "应付款日"),
    ("reminderTypeLabel", "催款状态"),
    ("overdueDays", "逾期天数"),
    ("daysUntilDue", "距应付款天数"),
    ("followupCount", "跟进次数"),
    ("lastFollowupTime", "最近跟进时间"),
    ("lastFollowupNote", "最近跟进备注"),
]


def _date_only(val: Any) -> str:
    text = str(val or "").strip()
    if not text:
        return ""
    return text[:10] if len(text) >= 10 else text


def _cell(item: dict[str, Any], key: str) -> Any:
    if key == "isFcl":
        return "是" if item.get("isFcl") else "否"
    if key == "statusCode":
        raw = (item.get("statusCode") or "").strip()
        if not raw:
            return "—"
        return _STATUS_LABELS.get(raw) or _STATUS_LABELS.get(raw.upper()) or raw
    if key == "paymentStatus":
        code = (item.get("paymentStatus") or "").strip().upper()
        if code == "PAID":
            return "已付款"
        if code == "UNPAID":
            return "未付款"
        return code or "—"
    if key == "channelNameZh":
        return (item.get("channelNameZh") or item.get("channelCode") or "").strip()
    if key in ("ata", "deliveredTime"):
        return _date_only(item.get(key))
    val = item.get(key)
    if val is None:
        return ""
    return val


def build_payment_reminder_export_bytes(items: list[dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "催款列表"
    ws.append([label for _, label in _EXPORT_COLUMNS])
    for item in items:
        ws.append([_cell(item, key) for key, _ in _EXPORT_COLUMNS])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
