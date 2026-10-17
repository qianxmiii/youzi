"""批量从 DPS 下载选中运单的货箱重量尺寸数据。"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path

from ..db.shipments_repository import ShipmentsRepository
from .dps_data_download import download_dps_cargo_data, safe_cargo_data_filename

MAX_DOWNLOAD_BATCH = 50


def cargo_download_zip_filename(when: datetime | None = None) -> str:
    """其它 DPS 批量下载沿用的 zip 名：年月日时分秒，如 20261017234530.zip"""
    ts = (when or datetime.now()).strftime("%Y%m%d%H%M%S")
    return f"{ts}.zip"


def cargo_data_batch_folder_name(count: int, when: datetime | None = None) -> str:
    """多票货箱：压缩包内文件夹名，与 zip 主文件名一致（无 .zip）。"""
    ts = (when or datetime.now()).strftime("%Y%m%d%H%M%S")
    return f"{count}票数据_{ts}"


def cargo_data_batch_zip_filename(count: int, when: datetime | None = None) -> str:
    """多票货箱压缩包：{票数}票数据_{年月日时分秒}.zip"""
    return f"{cargo_data_batch_folder_name(count, when)}.zip"


def _cargo_data_entry_filename(shipment_no: str, extension: str) -> str:
    """单票货箱文件：{运单号}_data.ext（不用 DPS 原名）。"""
    return safe_cargo_data_filename(shipment_no, extension)


def build_dps_cargo_data_download(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
) -> tuple[bytes, str, str]:
    """
    返回 (content, media_type, download_filename)。
    每票单独请求 DPS（?ids=单个 waybillId）。
    单票：{运单号}_data.ext；多票：各文件重命名后装入文件夹并打 zip（{N}票数据_{时间}.zip）。
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
            name = _cargo_data_entry_filename(
                shipment_no or label,
                downloaded.extension,
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

    when = datetime.now()
    folder = cargo_data_batch_folder_name(len(files), when)
    zip_name = cargo_data_batch_zip_filename(len(files), when)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files:
            zf.writestr(f"{folder}/{name}", content)
    return buf.getvalue(), "application/zip", zip_name
