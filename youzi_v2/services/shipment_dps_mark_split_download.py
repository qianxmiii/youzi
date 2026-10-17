"""单票唛头按工厂件数拆分下载。"""

from __future__ import annotations

from pathlib import Path

from ..db.shipments_repository import ShipmentsRepository
from .dps_mark_download import download_dps_single_mark
from .mark_pdf_split import (
    parse_mark_split_segments,
    split_mark_pdf_segments,
    zip_mark_split_files,
)


def build_dps_mark_split_download(
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_id: str,
    segments_raw: str | list[int],
    *,
    progress_cb=None,
) -> tuple[bytes, str, str]:
    def report(p: int, msg: str) -> None:
        if progress_cb:
            progress_cb(p, msg)
    sid = (shipment_id or "").strip()
    if not sid:
        raise ValueError("运单 id 不能为空")

    row = repo.get_by_id(sid)
    if row is None:
        raise ValueError("运单不存在")

    shipment_no = str(row.get("shipmentNo") or "").strip() or sid
    waybill_id = str(row.get("waybillId") or "").strip()
    if not waybill_id:
        raise ValueError(f"{shipment_no}: 无 DPS 运单 ID，请先「更新选中运单」")

    segments = parse_mark_split_segments(segments_raw)
    report(12, "正在从 DPS 下载唛头 PDF…")
    downloaded = download_dps_single_mark(config_path, waybill_id)
    ext = (downloaded.extension or "").lower()
    if ext != ".pdf":
        raise ValueError(f"唛头（拆分）仅支持 PDF，当前为 {ext or '未知格式'}")

    report(38, f"正在按 {len(segments)} 段拆分 PDF…")
    parts = split_mark_pdf_segments(downloaded.content, shipment_no, segments)
    total = sum(segments)
    report(78, "正在打包拆分唛头…")
    content, filename = zip_mark_split_files(shipment_no, parts, total_ctns=total)
    report(95, "即将完成…")
    return content, "application/zip", filename
