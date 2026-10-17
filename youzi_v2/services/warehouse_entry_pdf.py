"""进仓单 PDF：由同源 xlsx 转换（见 warehouse_entry_xlsx_to_pdf）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .warehouse_entry_template import (
    build_warehouse_entry_xlsx_from_template,
    load_warehouse_entry_special_remarks,
    resolve_warehouse_entry_template_path,
)
from .warehouse_entry_xlsx_to_pdf import convert_warehouse_entry_xlsx_bytes_to_pdf


def build_warehouse_entry_pdf_from_template(
    template_path: Path,
    shipments: list[dict[str, Any]],
    *,
    warehouse_key: str,
    warehouse_label: str,
    receive_address: str,
    special_remarks: str = "",
    when: datetime | None = None,
) -> bytes:
    """与 Excel 进仓单同一套模板填充，再转为 PDF。"""
    xlsx_bytes = build_warehouse_entry_xlsx_from_template(
        template_path,
        shipments,
        warehouse_key=warehouse_key,
        warehouse_label=warehouse_label,
        receive_address=receive_address,
        special_remarks=special_remarks,
        when=when,
    )
    return convert_warehouse_entry_xlsx_bytes_to_pdf(xlsx_bytes)


def build_warehouse_entry_pdf(
    shipments: list[dict[str, Any]],
    *,
    config_path: Path | None,
    warehouse_key: str,
    warehouse_label: str,
    receive_address: str,
    special_remarks: str = "",
    when: datetime | None = None,
) -> bytes:
    template_path = resolve_warehouse_entry_template_path(config_path)
    return build_warehouse_entry_pdf_from_template(
        template_path,
        shipments,
        warehouse_key=warehouse_key,
        warehouse_label=warehouse_label,
        receive_address=receive_address,
        special_remarks=special_remarks,
        when=when,
    )
