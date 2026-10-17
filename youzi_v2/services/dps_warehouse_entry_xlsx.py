"""进仓单 Excel 顶部写入收货地址。"""

from __future__ import annotations

import io

from openpyxl import load_workbook


def prepend_receive_address_to_xlsx(content: bytes, address_block: str) -> bytes:
    """
    在 xlsx 首 sheet 顶部插入收货地址行（仅 .xlsx；失败则原样返回）。
    """
    block = (address_block or "").strip()
    if not block or not content:
        return content
    try:
        wb = load_workbook(io.BytesIO(content))
    except Exception:
        return content
    ws = wb.active
    lines = block.split("\n")
    insert_count = len(lines) + 1
    ws.insert_rows(1, amount=insert_count)
    for idx, line in enumerate(lines, start=1):
        ws.cell(row=idx, column=1, value=line)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
