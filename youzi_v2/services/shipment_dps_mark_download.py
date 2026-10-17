"""勾选运单下载 DPS 唛头。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..db.shipments_repository import ShipmentsRepository
from .dps_data_download import resolve_dps_download_filename
from .dps_mark_download import (
    download_dps_batch_mark,
    download_dps_single_mark,
    safe_mark_filename,
)
from .shipment_dps_cargo_download import MAX_DOWNLOAD_BATCH

MAX_MARK_BATCH = MAX_DOWNLOAD_BATCH


def _mark_download_filename(extension: str) -> str:
    ext = extension if extension.startswith(".") else f".{extension}" if extension else ".zip"
    return f"{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"


def build_dps_mark_data_download(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
) -> tuple[bytes, str, str]:
    ids = [x.strip() for x in shipment_ids if x and x.strip()]
    if not ids:
        raise ValueError("运单 id 列表不能为空")
    if len(ids) > MAX_MARK_BATCH:
        raise ValueError(f"单次最多下载 {MAX_MARK_BATCH} 票唛头")

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
        raise ValueError(f"唛头下载失败：{detail}" if detail else "没有可下载的唛头")

    try:
        if len(entries) == 1:
            shipment_no, waybill_id = entries[0]
            downloaded = download_dps_single_mark(config_path, waybill_id)
            filename = resolve_dps_download_filename(
                downloaded,
                fallback=safe_mark_filename(shipment_no, downloaded.extension),
            )
        else:
            waybill_ids = [w for _, w in entries]
            downloaded = download_dps_batch_mark(config_path, waybill_ids)
            filename = _mark_download_filename(downloaded.extension)
    except Exception as exc:
        suffix = f"（另有 {len(errors)} 票未纳入）" if errors else ""
        raise ValueError(f"唛头下载失败：{exc}{suffix}") from exc

    return downloaded.content, downloaded.media_type, filename
