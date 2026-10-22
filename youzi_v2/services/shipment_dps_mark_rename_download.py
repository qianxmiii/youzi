"""勾选运单下载 DPS 唛头，并按字段顺序重命名。"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path

from ..db.shipments_repository import ShipmentsRepository
from .dps_mark_download import download_dps_single_mark
from .mark_rename import (
    build_mark_rename_folder,
    build_mark_rename_stem,
    load_country_label_map,
    normalize_mark_rename_country_lang,
    normalize_mark_rename_fields,
    normalize_mark_rename_folder,
    normalize_mark_rename_separator,
    unique_mark_filename,
)
from .shipment_dps_cargo_download import MAX_DOWNLOAD_BATCH


def build_dps_mark_rename_download(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
    fields_raw: list[str] | None,
    separator_raw: str | None,
    folder_raw: str | None = None,
    country_lang_raw: str | None = None,
    *,
    progress_cb=None,
) -> tuple[bytes, str, str]:
    def report(p: int, msg: str) -> None:
        if progress_cb:
            progress_cb(p, msg)

    ids = [x.strip() for x in shipment_ids if x and x.strip()]
    if not ids:
        raise ValueError("运单 id 列表不能为空")
    if len(ids) > MAX_DOWNLOAD_BATCH:
        raise ValueError(f"单次最多下载 {MAX_DOWNLOAD_BATCH} 票唛头")

    fields = normalize_mark_rename_fields(fields_raw)
    separator = normalize_mark_rename_separator(separator_raw)
    folder_key = normalize_mark_rename_folder(folder_raw)
    country_lang = normalize_mark_rename_country_lang(country_lang_raw)
    with repo._database.lock:
        country_labels = load_country_label_map(repo._conn)

    files: list[tuple[str, bytes, str]] = []
    errors: list[str] = []
    used_names: dict[str, set[str]] = {}
    total = len(ids)

    for index, sid in enumerate(ids, start=1):
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
        report(8 + int(70 * (index - 1) / total), f"正在下载唛头 {index}/{total} · {label}")
        try:
            downloaded = download_dps_single_mark(config_path, waybill_id)
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            continue
        stem = build_mark_rename_stem(
            row,
            fields,
            separator,
            country_lang=country_lang,
            country_labels=country_labels,
        )
        folder = (
            build_mark_rename_folder(
                row,
                folder_key,
                country_lang=country_lang,
                country_labels=country_labels,
            )
            if folder_key
            else ""
        )
        used = used_names.setdefault(folder, set())
        name = unique_mark_filename(stem, downloaded.extension or ".pdf", used)
        arc_name = f"{folder}/{name}" if folder else name
        files.append((arc_name, downloaded.content, downloaded.media_type or "application/pdf"))

    if errors:
        detail = "；".join(errors[:5])
        if len(errors) > 5:
            detail += f" 等 {len(errors)} 条"
        raise ValueError(f"唛头（重命名）下载失败：{detail}")
    if not files:
        raise ValueError("没有可下载的唛头")

    if len(files) == 1 and "/" not in files[0][0]:
        name, content, media_type = files[0]
        report(95, "即将完成…")
        return content, media_type, name

    report(88, "正在打包重命名唛头…")
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    zip_name = f"{len(files)}票唛头_{ts}.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content, _media in files:
            info = zipfile.ZipInfo(filename=name)
            info.flag_bits |= 0x800
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, content)
    report(95, "即将完成…")
    return buf.getvalue(), "application/zip", zip_name
