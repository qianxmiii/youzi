"""批量从 DPS 下载选中运单的货箱重量尺寸数据。"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path

from ..db.shipments_repository import ShipmentsRepository
from .dps_data_download import (
    download_dps_cargo_data,
    resolve_dps_download_filename,
    safe_cargo_data_filename,
)

MAX_DOWNLOAD_BATCH = 50


def cargo_download_zip_filename(when: datetime | None = None) -> str:
    """多票打包 zip：年月日时分秒，如 20261017234530.zip"""
    ts = (when or datetime.now()).strftime("%Y%m%d%H%M%S")
    return f"{ts}.zip"


def build_dps_cargo_data_download(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
) -> tuple[bytes, str, str]:
    """
    返回 (content, media_type, download_filename)。
    每票单独请求 DPS（?ids=单个 waybillId）；多票时 zip，文件名为年月日时分秒。
    """
    ids = [x.strip() for x in shipment_ids if x and x.strip()]
    if not ids:
        raise ValueError("运单 id 列表不能为空")
    if len(ids) > MAX_DOWNLOAD_BATCH:
        raise ValueError(f"单次最多下载 {MAX_DOWNLOAD_BATCH} 票货箱数据")

    files: list[tuple[str, bytes]] = []
    errors: list[str] = []
    used_names: set[str] = set()

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
        try:
            downloaded = download_dps_cargo_data(config_path, waybill_id)
            name = resolve_dps_download_filename(
                downloaded,
                fallback=safe_cargo_data_filename(shipment_no or label, downloaded.extension),
            )
            if name in used_names:
                stem, dot, ext = name.rpartition(".")
                suffix = 2
                while f"{stem}_{suffix}{dot}{ext}" in used_names:
                    suffix += 1
                name = f"{stem}_{suffix}{dot}{ext}"
            used_names.add(name)
            files.append((name, downloaded.content))
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    if not files:
        detail = "；".join(errors[:5])
        if len(errors) > 5:
            detail += f" 等 {len(errors)} 条"
        raise ValueError(f"货箱下载失败：{detail}" if detail else "没有可下载的货箱数据")

    if len(files) == 1:
        name, content = files[0]
        return content, "application/octet-stream", name

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files:
            zf.writestr(name, content)
    return buf.getvalue(), "application/zip", cargo_download_zip_filename()
