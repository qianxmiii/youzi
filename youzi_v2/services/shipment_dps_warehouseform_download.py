"""勾选运单下载 DPS 排仓单（超 50 票按 ids 分批请求）。"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path

from ..db.shipments_repository import ShipmentsRepository
from .dps_data_download import resolve_dps_download_filename
from .dps_warehouseform_download import (
    download_dps_warehouseform,
    safe_warehouseform_filename,
)
from .shipment_dps_cargo_download import MAX_DOWNLOAD_BATCH, cargo_download_zip_filename

MAX_WAREHOUSEFORM_BATCH = MAX_DOWNLOAD_BATCH


def _warehouseform_batch_fallback_filename(batch_index: int, extension: str) -> str:
    ext = extension if extension.startswith(".") else f".{extension}" if extension else ".zip"
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    if batch_index <= 1:
        return f"{ts}{ext}"
    return f"{ts}_batch{batch_index}{ext}"


def _chunk_list(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def build_dps_warehouseform_download(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
) -> tuple[bytes, str, str]:
    ids = [x.strip() for x in shipment_ids if x and x.strip()]
    if not ids:
        raise ValueError("运单 id 列表不能为空")

    entries: list[tuple[str, str]] = []
    errors: list[str] = []

    for sid in ids:
        row = repo.get_by_id(sid)
        if row is None:
            errors.append(f"{sid}: 运单不存在")
            continue
        shipment_no = str(row.get("shipmentNo") or "").strip()
        waybill_id = str(row.get("waybillId") or "").strip()
        label = shipment_no or sid
        if not waybill_id:
            errors.append(f"{label}: 无 DPS 运单 ID，请先「更新选中运单」")
            continue
        entries.append((shipment_no or label, waybill_id))

    if not entries:
        detail = "；".join(errors[:5])
        if len(errors) > 5:
            detail += f" 等 {len(errors)} 条"
        raise ValueError(f"排仓单下载失败：{detail}" if detail else "没有可下载的排仓单")

    waybill_ids = [w for _, w in entries]
    chunks = _chunk_list(waybill_ids, MAX_WAREHOUSEFORM_BATCH)
    batch_files: list[tuple[str, bytes]] = []
    used_names: set[str] = set()

    for batch_idx, chunk in enumerate(chunks, start=1):
        try:
            downloaded = download_dps_warehouseform(config_path, chunk)
        except Exception as exc:
            suffix = f"（第 {batch_idx}/{len(chunks)} 批）"
            raise ValueError(f"排仓单下载失败：{exc}{suffix}") from exc

        if len(entries) == 1 and len(chunks) == 1:
            shipment_no, _ = entries[0]
            filename = safe_warehouseform_filename(shipment_no, downloaded.extension)
            return downloaded.content, downloaded.media_type, filename

        fallback = _warehouseform_batch_fallback_filename(batch_idx, downloaded.extension)
        name = resolve_dps_download_filename(downloaded, fallback=fallback)
        if name in used_names:
            stem, dot, ext = name.rpartition(".")
            suffix = 2
            while f"{stem}_{suffix}{dot}{ext}" in used_names:
                suffix += 1
            name = f"{stem}_{suffix}{dot}{ext}"
        used_names.add(name)
        batch_files.append((name, downloaded.content))

    if len(batch_files) == 1:
        name, content = batch_files[0]
        return content, "application/octet-stream", name

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in batch_files:
            zf.writestr(name, content)
    return buf.getvalue(), "application/zip", cargo_download_zip_filename()
