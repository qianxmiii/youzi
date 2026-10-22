"""客户管理 Excel 导出。"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook

from .payment_reminder_rules import settlement_method_label

_EXPORT_COLUMNS: list[tuple[str, str]] = [
    ("customerName", "运单用户名"),
    ("customerLang", "客户语言"),
    ("isVip", "VIP"),
    ("shipmentCount", "运单数"),
    ("settlementMethod", "结算方式"),
    ("settlementDay", "月结日"),
    ("note", "备注"),
    ("createdTime", "创建时间"),
    ("updatedTime", "更新时间"),
]

_LANG_LABEL = {"zh": "中文", "en": "英文"}


def _cell(item: dict[str, Any], key: str) -> Any:
    if key == "customerLang":
        raw = (item.get("customerLang") or "zh").strip().lower()
        return _LANG_LABEL.get(raw, raw)
    if key == "isVip":
        return "是" if item.get("isVip") else "否"
    if key == "settlementMethod":
        return settlement_method_label(item.get("settlementMethod")) or ""
    if key == "settlementDay":
        day = item.get("settlementDay")
        if day is None:
            return ""
        return int(day)
    val = item.get(key)
    if val is None:
        return ""
    return val


def build_customer_export_bytes(items: list[dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "客户"
    ws.append([label for _, label in _EXPORT_COLUMNS])
    for item in items:
        ws.append([_cell(item, key) for key, _ in _EXPORT_COLUMNS])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
