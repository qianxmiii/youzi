"""客户地址簿 Excel 模板、导入与导出。"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook

from ..db.customer_addresses_repository import CustomerAddressesRepository
from ..db.customer_addresses_table import ADDRESS_KIND_LABELS, ADDRESS_KINDS

_HEADERS = [
    "客户名",
    "地址简称",
    "收货人名",
    "收货人公司名",
    "收货人电话",
    "收货人邮箱",
    "国家",
    "收件人地址",
    "收件人邮编",
    "地址类型",
    "偏远",
    "备注",
]

_SAMPLE = [
    "示例客户",
    "",
    "Alex Chen",
    "North Warehouse LLC",
    "+1 415 555 0100",
    "alex@example.com",
    "US",
    "123 Market St, San Francisco, CA",
    "94105",
    "商业",
    "否",
    "",
]

_KIND_ALIASES = {
    "海外仓": "WAREHOUSE",
    "仓库": "WAREHOUSE",
    "WAREHOUSE": "WAREHOUSE",
    "商业": "COMMERCIAL",
    "COMMERCIAL": "COMMERCIAL",
    "住宅": "RESIDENTIAL",
    "RESIDENTIAL": "RESIDENTIAL",
}

_REMOTE_YES = {"是", "1", "Y", "YES", "TRUE", "偏远"}
_REMOTE_NO = {"", "否", "0", "N", "NO", "FALSE"}


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_kind(value: str) -> str:
    key = value.strip()
    kind = _KIND_ALIASES.get(key) or _KIND_ALIASES.get(key.upper())
    if kind not in ADDRESS_KINDS:
        raise ValueError("地址类型须为海外仓、商业或住宅")
    return kind


def _parse_remote(value: str) -> bool:
    key = value.strip()
    upper = key.upper()
    if key in _REMOTE_YES or upper in _REMOTE_YES:
        return True
    if key in _REMOTE_NO or upper in _REMOTE_NO:
        return False
    raise ValueError("偏远须填是或否")


def build_template_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "客户地址"
    ws.append(_HEADERS)
    ws.append(_SAMPLE)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _item_to_row(item: dict[str, Any]) -> list[Any]:
    kind = str(item.get("addressKind") or "")
    return [
        item.get("customerName") or "",
        item.get("label") or "",
        item.get("consigneeName") or "",
        item.get("company") or "",
        item.get("phone") or "",
        item.get("email") or "",
        item.get("country") or "",
        item.get("address") or "",
        item.get("postcode") or "",
        ADDRESS_KIND_LABELS.get(kind, kind),
        "是" if item.get("isRemote") else "否",
        item.get("note") or "",
    ]


def build_export_bytes(items: list[dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "客户地址"
    ws.append(_HEADERS)
    for item in items:
        ws.append(_item_to_row(item))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def import_excel_file(
    repo: CustomerAddressesRepository,
    file_path: Path,
) -> dict[str, Any]:
    wb = load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    header = next(rows, None)
    if header is None:
        return {"created": 0, "failed": 1, "errors": [{"row": 1, "message": "空文件"}]}
    index = {_cell(name): pos for pos, name in enumerate(header) if _cell(name)}
    missing = [name for name in ("客户名", "国家", "收件人地址", "地址类型") if name not in index]
    if missing:
        return {
            "created": 0,
            "failed": 1,
            "errors": [{"row": 1, "message": "缺少列：" + "、".join(missing)}],
        }

    def pick(row: tuple[Any, ...], name: str) -> str:
        pos = index.get(name)
        if pos is None or pos >= len(row):
            return ""
        return _cell(row[pos])

    created = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    for offset, row in enumerate(rows, start=2):
        if row is None or not any(_cell(cell) for cell in row):
            continue
        try:
            repo.insert_row(
                {
                    "customerName": pick(row, "客户名"),
                    "label": pick(row, "地址简称"),
                    "consigneeName": pick(row, "收货人名"),
                    "company": pick(row, "收货人公司名"),
                    "phone": pick(row, "收货人电话"),
                    "email": pick(row, "收货人邮箱"),
                    "country": pick(row, "国家"),
                    "address": pick(row, "收件人地址"),
                    "postcode": pick(row, "收件人邮编"),
                    "addressKind": _parse_kind(pick(row, "地址类型")),
                    "isRemote": _parse_remote(pick(row, "偏远")),
                    "note": pick(row, "备注"),
                }
            )
            created += 1
        except ValueError as exc:
            failed += 1
            if len(errors) < 50:
                errors.append({"row": offset, "message": str(exc)})
    wb.close()
    return {"created": created, "failed": failed, "errors": errors}
