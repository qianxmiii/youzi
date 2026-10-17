"""勾选运单下载 DPS 箱单发票。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..db.shipments_repository import ShipmentsRepository
from .dps_data_download import resolve_dps_download_filename
from .dps_packinglist_download import (
    download_dps_packinglist,
    safe_packinglist_filename,
)
from .shipment_dps_cargo_download import MAX_DOWNLOAD_BATCH

MAX_PACKINGLIST_BATCH = MAX_DOWNLOAD_BATCH


def _packinglist_batch_fallback_filename(extension: str) -> str:
    ext = extension if extension.startswith(".") else f".{extension}" if extension else ".zip"
    return f"{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"


def build_dps_packinglist_download(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
) -> tuple[bytes, str, str]:
    ids = [x.strip() for x in shipment_ids if x and x.strip()]
    if not ids:
        raise ValueError("运单 id 列表不能为空")
    if len(ids) > MAX_PACKINGLIST_BATCH:
        raise ValueError(f"单次最多下载 {MAX_PACKINGLIST_BATCH} 票箱单发票")

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
        raise ValueError(f"箱单发票下载失败：{detail}" if detail else "没有可下载的箱单发票")

    waybill_ids = [w for _, w in entries]

    try:
        downloaded = download_dps_packinglist(config_path, waybill_ids)
        if len(entries) == 1:
            shipment_no, _ = entries[0]
            filename = safe_packinglist_filename(shipment_no, downloaded.extension)
        else:
            filename = resolve_dps_download_filename(
                downloaded,
                fallback=_packinglist_batch_fallback_filename(downloaded.extension),
            )
    except Exception as exc:
        suffix = f"（另有 {len(errors)} 票未纳入）" if errors else ""
        raise ValueError(f"箱单发票下载失败：{exc}{suffix}") from exc

    return downloaded.content, downloaded.media_type, filename
