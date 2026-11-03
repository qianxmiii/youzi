"""自生成唛头 PDF：102mm × 102mm，一页一件。"""

from __future__ import annotations

import io
import re
from typing import Any

from reportlab.graphics.barcode import code128
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

PAGE_SIZE_MM = 102.0
PAGE_SIZE = PAGE_SIZE_MM * mm  # ≈ 289.13pt；参考样例 mediabox 约 290pt
_MADE_IN_CHINA = "MADE IN CHINA"
_INVALID_FS = re.compile(r'[\\/:*?"<>|\r\n\t]+')
_WHITESPACE = re.compile(r"\s+")

_FONT_REGISTERED = False
_FONT_NAME = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"


def _ensure_fonts() -> None:
    """优先注册微软雅黑（与参考样例一致），失败则回退 Helvetica。"""
    global _FONT_REGISTERED, _FONT_NAME, _FONT_BOLD
    if _FONT_REGISTERED:
        return
    _FONT_REGISTERED = True
    candidates = (
        (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"),
        (r"C:\Windows\Fonts\msyh.ttf", r"C:\Windows\Fonts\msyhbd.ttf"),
    )
    for regular, bold in candidates:
        try:
            pdfmetrics.registerFont(TTFont("MarkSelfYaHei", regular, subfontIndex=0))
            try:
                pdfmetrics.registerFont(TTFont("MarkSelfYaHei-Bold", bold, subfontIndex=0))
                _FONT_BOLD = "MarkSelfYaHei-Bold"
            except Exception:
                _FONT_BOLD = "MarkSelfYaHei"
            _FONT_NAME = "MarkSelfYaHei"
            return
        except Exception:
            continue


def barcode_value(shipment_no: str, package_index: int) -> str:
    """DPS 运单号 + 后 4 位序号，如 DPSECO260820040001。"""
    base = (shipment_no or "").strip()
    if not base:
        raise ValueError("运单号不能为空")
    if package_index < 1:
        raise ValueError("箱序号须从 1 开始")
    return f"{base}{package_index:04d}"


def _text(value: Any) -> str:
    if value is None:
        return ""
    return _WHITESPACE.sub(" ", str(value).strip())


def safe_mark_self_stem(shipment_no: str) -> str:
    stem = _INVALID_FS.sub("_", (shipment_no or "").strip()) or "mark"
    stem = _WHITESPACE.sub(" ", stem).strip(" ._") or "mark"
    return stem


def safe_mark_self_filename(shipment_no: str) -> str:
    return f"{safe_mark_self_stem(shipment_no)}.pdf"


def build_mark_self_pdf_bytes(
    *,
    channel_name: str,
    shipment_no: str,
    customer_no: str,
    ctns: int,
    country_code: str,
    zipcode: str,
) -> bytes:
    """生成多页唛头 PDF；页数 = 件数，每页 PKG:i/N。"""
    total = int(ctns)
    if total < 1:
        raise ValueError("件数须至少为 1")
    sn = _text(shipment_no)
    if not sn:
        raise ValueError("运单号不能为空")

    _ensure_fonts()
    channel = _text(channel_name) or sn
    cust = _text(customer_no)
    country = _text(country_code).upper()
    zip_text = _text(zipcode)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_SIZE, PAGE_SIZE))

    # 垂直节奏：全文加粗；条码高度减半，上下各留边距
    y_channel = PAGE_SIZE - 12 * mm
    y_shipment = PAGE_SIZE - 21 * mm
    y_customer = PAGE_SIZE - 29 * mm
    barcode_height = 14 * mm
    barcode_pad = 4 * mm
    barcode_top = y_customer - barcode_pad - 3 * mm  # 客户单号下方留空再画条码
    barcode_bottom = barcode_top - barcode_height
    y_pkg = barcode_bottom - barcode_pad - 4 * mm
    y_country = y_pkg - 8 * mm
    y_zip = y_country - 8 * mm
    y_made = y_zip - 9 * mm

    for i in range(1, total + 1):
        c.setFont(_FONT_BOLD, 16)
        c.drawCentredString(PAGE_SIZE / 2, y_channel, channel)
        c.drawCentredString(PAGE_SIZE / 2, y_shipment, sn)
        if cust:
            c.drawCentredString(PAGE_SIZE / 2, y_customer, cust)

        value = barcode_value(sn, i)
        # 条宽随内容长度自适应，限制在页宽内
        bar_width = 1.0
        while True:
            barcode = code128.Code128(
                value,
                barHeight=barcode_height,
                barWidth=bar_width,
                humanReadable=False,
                quiet=False,
            )
            if barcode.width <= PAGE_SIZE - 10 * mm or bar_width <= 0.45:
                break
            bar_width -= 0.05
        barcode.drawOn(c, (PAGE_SIZE - barcode.width) / 2, barcode_bottom)

        c.setFont(_FONT_BOLD, 15)
        c.drawCentredString(PAGE_SIZE / 2, y_pkg, f"PKG:{i}/{total}")
        if country:
            c.drawCentredString(PAGE_SIZE / 2, y_country, country)
        if zip_text:
            c.drawCentredString(PAGE_SIZE / 2, y_zip, zip_text)
        c.setFont(_FONT_BOLD, 16)
        c.drawCentredString(PAGE_SIZE / 2, y_made, _MADE_IN_CHINA)

        c.showPage()

    c.save()
    return buf.getvalue()
