"""进仓单 xlsx → PDF（先与 Excel 下载同源生成，再转换，保证版式一致）。"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_XL_TYPE_PDF = 0
_EXCEL_CANDIDATES = (
    Path(r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"),
    Path(r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE"),
    Path(r"C:\Program Files\Microsoft Office\root\Office15\EXCEL.EXE"),
    Path(r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE"),
    Path(r"C:\Program Files\Microsoft Office\Office15\EXCEL.EXE"),
    Path(r"C:\Program Files\Microsoft Office\Office14\EXCEL.EXE"),
)
_LIBREOFFICE_CANDIDATES = (
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    Path("/usr/bin/libreoffice"),
    Path("/usr/bin/soffice"),
)


def _find_soffice() -> Path | None:
    env = (os.environ.get("YOUZI_LIBREOFFICE") or "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return Path(found)
    for p in _LIBREOFFICE_CANDIDATES:
        if p.is_file():
            return p
    return None


def _win32com_importable() -> bool:
    if os.name != "nt":
        return False
    try:
        import win32com.client  # noqa: F401

        return True
    except ImportError:
        return False


def _convert_via_win32com(xlsx_path: Path, pdf_path: Path) -> None:
    import win32com.client  # pywin32

    # DispatchEx：独立进程，避免占用用户已打开的 Excel
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    wb = None
    try:
        wb = excel.Workbooks.Open(str(xlsx_path.resolve()))
        wb.ExportAsFixedFormat(_XL_TYPE_PDF, str(pdf_path.resolve()))
    finally:
        if wb is not None:
            wb.Close(False)
        excel.Quit()


def _convert_via_libreoffice(xlsx_path: Path, pdf_path: Path, soffice: Path) -> None:
    out_dir = pdf_path.parent
    subprocess.run(
        [
            str(soffice),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(xlsx_path),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    produced = out_dir / f"{xlsx_path.stem}.pdf"
    if not produced.is_file():
        raise FileNotFoundError(f"LibreOffice 未生成 PDF：{produced}")
    if produced.resolve() != pdf_path.resolve():
        produced.replace(pdf_path)


def convert_warehouse_entry_xlsx_bytes_to_pdf(xlsx_bytes: bytes) -> bytes:
    """将进仓单 xlsx 字节转为 PDF。Windows 优先 Excel COM；否则 LibreOffice。"""
    if not xlsx_bytes:
        raise ValueError("进仓单 xlsx 为空")

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="youzi-wh-entry-") as td:
        td_path = Path(td)
        xlsx_path = td_path / "warehouse_entry.xlsx"
        pdf_path = td_path / "warehouse_entry.pdf"
        xlsx_path.write_bytes(xlsx_bytes)

        # Windows：有 pywin32 即尝试 COM（Click-to-Run 等路径可能不在候选列表里）
        if _win32com_importable():
            try:
                _convert_via_win32com(xlsx_path, pdf_path)
                if pdf_path.is_file() and pdf_path.stat().st_size > 0:
                    return pdf_path.read_bytes()
                errors.append("Excel 转 PDF 未生成文件")
            except Exception as exc:
                errors.append(f"Excel 转 PDF 失败：{exc}")
        elif os.name == "nt":
            errors.append(
                "未安装 pywin32（pip install pywin32），无法用本机 Excel 转 PDF"
            )

        soffice = _find_soffice()
        if soffice is not None:
            try:
                _convert_via_libreoffice(xlsx_path, pdf_path, soffice)
                return pdf_path.read_bytes()
            except Exception as exc:
                errors.append(f"LibreOffice 转 PDF 失败：{exc}")
        else:
            errors.append(
                "未找到 LibreOffice（可安装或设置环境变量 YOUZI_LIBREOFFICE 指向 soffice）"
            )

    hint = (
        "进仓单 PDF 需先将 Excel 转为 PDF："
        "Windows 请安装 Microsoft Excel 并执行 pip install pywin32；"
        "Linux 请安装 LibreOffice 或配置 YOUZI_LIBREOFFICE。"
    )
    detail = "；".join(errors) if errors else "无可用转换器"
    raise RuntimeError(f"{hint}（{detail}）")
