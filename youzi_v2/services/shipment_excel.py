"""运单 Excel 解析与导入（对齐运单数据导出模板）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from youzi_v2.db.shipments_repository import ShipmentsRepository

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "shipment_excel_columns.json"


def _load_mapping() -> dict[str, Any]:
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _cell_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _cell_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _infer_address_type(
    customer_no: str | None,
    address_code: str | None,
    delivery_address: str | None,
) -> str | None:
    blob = " ".join(
        x for x in (customer_no or "", address_code or "", delivery_address or "") if x
    ).upper()
    if "FBA" in blob or (customer_no or "").upper().startswith("FBA"):
        return "AMZ"
    if "WFS" in blob:
        return "WFS"
    if "3PL" in blob:
        return "3PL"
    return None


def _normalize_country(raw: str | None, aliases: dict[str, str]) -> str | None:
    if not raw:
        return None
    text = raw.strip()
    return aliases.get(text, text)


def _pick_sheet(wb: Any, names: list[str]) -> Any:
    for name in names:
        if name in wb.sheetnames:
            return wb[name]
    return wb.active


def parse_excel_rows(
    file_path: Path,
) -> tuple[list[tuple[int, dict[str, Any]]], list[dict[str, Any]]]:
    """
    解析 Excel，返回 ([(excel行号, payload), ...], 错误列表)。
    payload 键为数据库蛇形字段名。
    """
    mapping = _load_mapping()
    col_map: dict[str, str] = mapping["columns"]
    country_aliases: dict[str, str] = mapping.get("country_aliases", {})
    sheet_names: list[str] = mapping.get("sheet_preference", [])

    wb = load_workbook(file_path, read_only=True, data_only=True)
    try:
        ws = _pick_sheet(wb, sheet_names)
        rows_iter = ws.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            return [], [{"row": 1, "message": "空文件"}]

        header_index: dict[int, str] = {}
        for idx, cell in enumerate(header_row):
            label = _cell_str(cell)
            if label and label in col_map:
                header_index[idx] = col_map[label]

        if "shipment_no" not in header_index.values():
            return [], [{"row": 1, "message": "缺少表头「运单号」"}]

        payloads: list[tuple[int, dict[str, Any]]] = []
        errors: list[dict[str, Any]] = []
        excel_row = 1
        for row in rows_iter:
            excel_row += 1
            if not row or all(c is None or str(c).strip() == "" for c in row):
                continue
            record: dict[str, Any] = {}
            for idx, field in header_index.items():
                val = row[idx] if idx < len(row) else None
                if field == "ctns":
                    record[field] = _cell_int(val)
                else:
                    record[field] = _cell_str(val)

            shipment_no = (record.get("shipment_no") or "").strip()
            if not shipment_no:
                errors.append({"row": excel_row, "message": "运单号为空，已跳过"})
                continue

            record["country_code"] = _normalize_country(
                record.get("country_code"), country_aliases
            )
            record["address_type"] = _infer_address_type(
                record.get("customer_no"),
                record.get("address_code"),
                record.get("delivery_address"),
            )
            if not record.get("status_code"):
                record["status_code"] = "UNKNOWN"

            payloads.append((excel_row, record))
        return payloads, errors
    finally:
        wb.close()


def import_excel_file(
    repo: ShipmentsRepository,
    file_path: Path,
) -> dict[str, Any]:
    rows, parse_errors = parse_excel_rows(file_path)
    created = 0
    updated = 0
    errors = list(parse_errors)
    for excel_row, payload in rows:
        try:
            _, is_new = repo.upsert_by_shipment_no(payload)
            if is_new:
                created += 1
            else:
                updated += 1
        except Exception as exc:  # noqa: BLE001 — 汇总行级错误
            errors.append(
                {
                    "row": excel_row,
                    "message": str(exc),
                    "shipmentNo": payload.get("shipment_no"),
                }
            )
    return {
        "ok": True,
        "totalRows": len(rows),
        "created": created,
        "updated": updated,
        "failed": len(errors),
        "errors": errors[:50],
    }
