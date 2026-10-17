"""唛头 PDF 按件数（页）拆分为多份。"""

from __future__ import annotations

import io
import re
import zipfile
from typing import Iterable

from pypdf import PdfReader, PdfWriter

_SEGMENT_RE = re.compile(r"[\s,，、]+")


def parse_mark_split_segments(raw: str | Iterable[int]) -> list[int]:
    """解析拆分件数，如「1 2 2」→ [1, 2, 2]。"""
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise ValueError("请填写拆分件数（如 1 2 2）")
        parts = [p for p in _SEGMENT_RE.split(text) if p.strip()]
        if not parts:
            raise ValueError("请填写拆分件数（如 1 2 2）")
        segments: list[int] = []
        for p in parts:
            try:
                n = int(p.strip())
            except ValueError as exc:
                raise ValueError(f"拆分件数须为正整数，无法解析：{p}") from exc
            if n <= 0:
                raise ValueError(f"拆分件数须为正整数：{n}")
            segments.append(n)
        return segments
    segments = [int(x) for x in raw]
    if not segments:
        raise ValueError("拆分件数不能为空")
    for n in segments:
        if n <= 0:
            raise ValueError(f"拆分件数须为正整数：{n}")
    return segments


def _safe_shipment_stem(shipment_no: str) -> str:
    base = (shipment_no or "").strip() or "运单"
    for ch in '\\/:*?"<>|':
        base = base.replace(ch, "_")
    return base


def _seq_range_label(start: int, end: int) -> str:
    if start == end:
        return str(start)
    return f"{start}-{end}"


def split_mark_pdf_segments(
    pdf_bytes: bytes,
    shipment_no: str,
    segments: list[int],
) -> list[tuple[str, bytes]]:
    """
    按 segments 顺序切分 PDF（每页对应一件）。
    文件名：{运单号}_{开始-结束}_{件数}ctns.pdf（仅 1 页时为 {运单号}_{序号}_{件数}ctns.pdf）
    """
    if not pdf_bytes:
        raise ValueError("唛头文件为空")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    need = sum(segments)
    if page_count != need:
        raise ValueError(
            f"唛头 PDF 共 {page_count} 页，与拆分件数合计 {need} 不一致（{' '.join(str(x) for x in segments)}）"
        )

    stem = _safe_shipment_stem(shipment_no)
    out: list[tuple[str, bytes]] = []
    cursor = 0
    start_seq = 1
    for n in segments:
        writer = PdfWriter()
        for _ in range(n):
            writer.add_page(reader.pages[cursor])
            cursor += 1
        end_seq = start_seq + n - 1
        seq = _seq_range_label(start_seq, end_seq)
        name = f"{stem}_{seq}_{n}ctns.pdf"
        buf = io.BytesIO()
        writer.write(buf)
        out.append((name, buf.getvalue()))
        start_seq = end_seq + 1
    return out


def zip_mark_split_files(
    shipment_no: str,
    files: list[tuple[str, bytes]],
    *,
    total_ctns: int | None = None,
) -> tuple[bytes, str]:
    total = total_ctns if total_ctns is not None else sum(
        int(name.rsplit("_", 2)[-1].replace("ctns.pdf", ""))
        for name, _ in files
        if "ctns.pdf" in name
    )
    if total <= 0 and files:
        total = len(files)
    stem = _safe_shipment_stem(shipment_no)
    zip_name = f"{stem}_{total}ctns.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arc_name, data in files:
            zf.writestr(arc_name, data)
    return buf.getvalue(), zip_name
