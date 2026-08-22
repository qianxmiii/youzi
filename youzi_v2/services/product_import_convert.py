"""箱单发票 → 产品导入模版（调用 tools/product_import 脚本）。"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

from youzi_v2.context import (
    CONFIG_PATH,
    OUTPUT_DIR,
    SCRIPT_PATH,
    UPLOAD_DIR,
    resolve_template_xls,
)


def convert_invoice_to_product_import(upload_bytes: bytes, *, suffix: str = ".xlsx") -> dict[str, str]:
    """写入临时箱单并生成产品导入 xls，返回 {id, filename}。"""
    task_id = str(uuid.uuid4())
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    if ext.lower() not in {".xls", ".xlsx", ".xlsm"}:
        ext = ".xlsx"
    upload_path = UPLOAD_DIR / f"{task_id}{ext}"
    output_path = OUTPUT_DIR / f"{task_id}.xls"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    upload_path.write_bytes(upload_bytes)
    try:
        template_path = resolve_template_xls()
        python_bin = os.environ.get("PYTHON", "python")
        cmd = [
            python_bin,
            str(SCRIPT_PATH),
            "--invoice",
            str(upload_path),
            "--template",
            str(template_path),
            "--config",
            str(CONFIG_PATH),
            "--output",
            str(output_path),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "转换失败").strip()
            raise ValueError(message)
        if not output_path.is_file():
            raise ValueError("转换完成但未生成输出文件")
    finally:
        upload_path.unlink(missing_ok=True)

    return {"id": task_id, "filename": "产品导入模版.xls"}


def product_import_output_path(task_id: str) -> Path:
    return OUTPUT_DIR / f"{task_id}.xls"
