"""勾选运单生成自有唛头 PDF（不经 DPS）。"""

from __future__ import annotations

import io
import zipfile
from typing import Any

from ..db.shipments_repository import ShipmentsRepository
from .mark_rename import mark_batch_zip_filename, shipment_ctns_count, unique_mark_filename
from .mark_self_pdf import build_mark_self_pdf_bytes, safe_mark_self_stem
from .shipment_dps_cargo_download import MAX_DOWNLOAD_BATCH


def _channel_name_en(repo: ShipmentsRepository, channel_code: str) -> str:
    code = (channel_code or "").strip()
    if not code:
        return ""
    with repo._database.lock:
        row = repo._conn.execute(
            "SELECT name_en, name_zh FROM channel_codes WHERE code = ? LIMIT 1",
            (code,),
        ).fetchone()
    if row is None:
        return ""
    return (row["name_en"] or row["name_zh"] or "").strip()


def _resolve_channel_label(repo: ShipmentsRepository, row: dict[str, Any]) -> str:
    en = _channel_name_en(repo, str(row.get("channelCode") or ""))
    if en:
        return en
    zh = str(row.get("channelNameZh") or "").strip()
    if zh:
        return zh
    return str(row.get("channelCode") or "").strip()


def build_mark_self_download(
    repo: ShipmentsRepository,
    shipment_ids: list[str],
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

    files: list[tuple[str, bytes]] = []
    errors: list[str] = []
    used_names: set[str] = set()
    total = len(ids)
    ctns_total = 0

    for index, sid in enumerate(ids, start=1):
        row = repo.get_by_id(sid)
        if row is None:
            errors.append(f"{sid}: 运单不存在")
            continue
        shipment_no = str(row.get("shipmentNo") or "").strip()
        label = shipment_no or sid
        ctns = shipment_ctns_count(row)
        if not shipment_no:
            errors.append(f"{label}: 运单号为空")
            continue
        if ctns < 1:
            errors.append(f"{label}: 件数无效，无法生成唛头")
            continue

        report(8 + int(70 * (index - 1) / total), f"正在生成唛头 {index}/{total} · {label}")
        try:
            pdf_bytes = build_mark_self_pdf_bytes(
                channel_name=_resolve_channel_label(repo, row),
                shipment_no=shipment_no,
                customer_no=str(row.get("customerNo") or ""),
                ctns=ctns,
                country_code=str(row.get("countryCode") or ""),
                zipcode=str(row.get("zipcode") or ""),
            )
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            continue

        name = unique_mark_filename(safe_mark_self_stem(shipment_no), ".pdf", used_names)
        files.append((name, pdf_bytes))
        ctns_total += ctns

    if errors:
        detail = "；".join(errors[:5])
        if len(errors) > 5:
            detail += f" 等 {len(errors)} 条"
        raise ValueError(f"唛头（自生成）失败：{detail}")
    if not files:
        raise ValueError("没有可生成的唛头")

    if len(files) == 1:
        name, content = files[0]
        report(95, "即将完成…")
        return content, "application/pdf", name

    report(88, "正在打包自生成唛头…")
    zip_name = mark_batch_zip_filename(len(files), ctns_total).replace(
        "件唛头_",
        "件唛头(自生成)_",
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files:
            info = zipfile.ZipInfo(filename=name)
            info.flag_bits |= 0x800
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, content)
    report(95, "即将完成…")
    return buf.getvalue(), "application/zip", zip_name
