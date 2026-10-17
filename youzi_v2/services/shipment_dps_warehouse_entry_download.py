"""勾选运单生成进仓单（模板填充，命名 {N}票进仓单_{年月日}）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..db.shipments_repository import ShipmentsRepository
from .dps_receive_warehouse import (
    collect_shipments_receive_warehouse,
    format_receive_address_block,
    require_receive_warehouse_address,
)
from .dps_warehouse_entry_download import warehouse_entry_download_filename
from .warehouse_entry_pdf import build_warehouse_entry_pdf
from .warehouse_entry_template import (
    build_warehouse_entry_xlsx_from_template,
    load_warehouse_entry_special_remarks,
    resolve_warehouse_entry_template_path,
)


def _load_shipment_rows(
    repo: ShipmentsRepository,
    shipment_ids: list[str],
) -> list[dict]:
    ids = [x.strip() for x in shipment_ids if x and x.strip()]
    if not ids:
        raise ValueError("运单 id 列表不能为空")
    rows: list[dict] = []
    for sid in ids:
        row = repo.get_by_id(sid)
        if row is None:
            raise ValueError(f"{sid}: 运单不存在")
        rows.append(row)
    return rows


def preview_receive_warehouse_for_shipments(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
) -> dict[str, str | int]:
    rows = _load_shipment_rows(repo, shipment_ids)
    warehouse_key, sample_origin = collect_shipments_receive_warehouse(rows)
    address = require_receive_warehouse_address(config_path, warehouse_key)
    block = format_receive_address_block(warehouse_key, address)

    return {
        "warehouseKey": warehouse_key,
        "warehouseLabel": sample_origin,
        "address": address,
        "addressBlock": block,
        "shipmentCount": len(rows),
    }


def build_dps_warehouse_entry_download(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
) -> tuple[bytes, str, str]:
    rows = _load_shipment_rows(repo, shipment_ids)
    preview = preview_receive_warehouse_for_shipments(repo, config_path, shipment_ids)
    warehouse_key = str(preview["warehouseKey"])
    warehouse_label = str(preview["warehouseLabel"])
    address = str(preview["address"])
    count = len(rows)

    template_path = resolve_warehouse_entry_template_path(config_path)
    special_remarks = load_warehouse_entry_special_remarks(config_path, warehouse_key)
    when = datetime.now()
    content = build_warehouse_entry_xlsx_from_template(
        template_path,
        rows,
        warehouse_key=warehouse_key,
        warehouse_label=warehouse_label,
        receive_address=address,
        special_remarks=special_remarks,
        when=when,
    )
    filename = warehouse_entry_download_filename(count, ".xlsx", when=when)
    return content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename


def build_dps_warehouse_entry_pdf_download(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
) -> tuple[bytes, str, str]:
    rows = _load_shipment_rows(repo, shipment_ids)
    preview = preview_receive_warehouse_for_shipments(repo, config_path, shipment_ids)
    warehouse_key = str(preview["warehouseKey"])
    warehouse_label = str(preview["warehouseLabel"])
    address = str(preview["address"])
    count = len(rows)

    special_remarks = load_warehouse_entry_special_remarks(config_path, warehouse_key)
    when = datetime.now()
    content = build_warehouse_entry_pdf(
        rows,
        config_path=config_path,
        warehouse_key=warehouse_key,
        warehouse_label=warehouse_label,
        receive_address=address,
        special_remarks=special_remarks,
        when=when,
    )
    filename = warehouse_entry_download_filename(count, ".pdf", when=when)
    return content, "application/pdf", filename
