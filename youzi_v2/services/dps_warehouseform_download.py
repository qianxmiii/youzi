"""DPS 排仓单下载（config.dps_warehouseform_download）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from .dps_data_download import (
    DpsCargoDataFile,
    _parse_binary_response,
    build_dps_data_download_url,
)
from .shipment_query_config import load_config_json, resolve_dps_authorization

CONFIG_KEY = "dps_warehouseform_download"
DEFAULT_TIMEOUT = 60


def load_dps_warehouseform_download_config(config_path: Path) -> dict[str, Any]:
    config = load_config_json(config_path)
    raw = config.get(CONFIG_KEY)
    block = raw if isinstance(raw, dict) else {}
    method = (block.get("method") or "POST").strip().upper()
    if method not in ("GET", "POST"):
        method = "POST"
    return {
        "url": (block.get("url") or "").strip(),
        "authorization": resolve_dps_authorization(config, block),
        "timeout": int(block.get("timeout") or DEFAULT_TIMEOUT),
        "method": method,
    }


def require_dps_warehouseform_download_config(config_path: Path) -> dict[str, Any]:
    cfg = load_dps_warehouseform_download_config(config_path)
    if not cfg["url"]:
        raise ValueError(f"config.json 缺少 {CONFIG_KEY}.url")
    if not cfg["authorization"]:
        raise ValueError("config.json 缺少 dps_authorization（或块内 Authorization）")
    return cfg


def safe_warehouseform_filename(stem: str, extension: str) -> str:
    base = (stem or "").strip() or "运单"
    for ch in '\\/:*?"<>|':
        base = base.replace(ch, "_")
    ext = extension if extension.startswith(".") else f".{extension}" if extension else ".xlsx"
    return f"{base}_排仓单{ext}"


def download_dps_warehouseform(
    config_path: Path,
    dps_waybill_ids: list[str],
    *,
    timeout: int | None = None,
) -> DpsCargoDataFile:
    """
    排仓单：POST/GET + URL ?ids=waybillId（多票英文逗号拼接，无 body）。
    单次请求 ids 建议不超过 50 个。
    """
    cfg = require_dps_warehouseform_download_config(config_path)
    ids = [str(x).strip() for x in dps_waybill_ids if str(x).strip()]
    if not ids:
        raise ValueError("排仓单 waybill id 不能为空")
    if len(ids) > 50:
        raise ValueError("排仓单单次请求 ids 不能超过 50 个")

    url = build_dps_data_download_url(cfg["url"], ids)
    headers = {
        "Authorization": cfg["authorization"],
        "Accept": "*/*",
    }
    req_timeout = timeout if timeout is not None else cfg["timeout"]
    if cfg["method"] == "POST":
        resp = requests.post(url, headers=headers, timeout=req_timeout)
    else:
        resp = requests.get(url, headers=headers, timeout=req_timeout)

    resp.raise_for_status()
    return _parse_binary_response(resp)
