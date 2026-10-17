"""DPS 进仓单下载（config.dps_warehouse_entry_download，缺省回退 dps_warehouseform_download）。"""

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

CONFIG_KEY = "dps_warehouse_entry_download"
FALLBACK_CONFIG_KEY = "dps_warehouseform_download"
DEFAULT_TIMEOUT = 60


def load_dps_warehouse_entry_download_config(config_path: Path) -> dict[str, Any]:
    config = load_config_json(config_path)
    block = config.get(CONFIG_KEY)
    if not isinstance(block, dict) or not (block.get("url") or "").strip():
        block = config.get(FALLBACK_CONFIG_KEY)
    if not isinstance(block, dict):
        block = {}
    method = (block.get("method") or "POST").strip().upper()
    if method not in ("GET", "POST"):
        method = "POST"
    warehouse_param = (
        block.get("warehouseQueryParam")
        or block.get("warehouse_query_param")
        or "warehouseCode"
    )
    warehouse_param = str(warehouse_param).strip()
    return {
        "url": (block.get("url") or "").strip(),
        "authorization": resolve_dps_authorization(config, block),
        "timeout": int(block.get("timeout") or DEFAULT_TIMEOUT),
        "method": method,
        "warehouse_query_param": warehouse_param,
    }


def require_dps_warehouse_entry_download_config(config_path: Path) -> dict[str, Any]:
    cfg = load_dps_warehouse_entry_download_config(config_path)
    if not cfg["url"]:
        raise ValueError(
            f"config.json 缺少 {CONFIG_KEY}.url（或 {FALLBACK_CONFIG_KEY}.url）"
        )
    if not cfg["authorization"]:
        raise ValueError("config.json 缺少 dps_authorization（或块内 Authorization）")
    return cfg


def warehouse_entry_download_filename(count: int, extension: str, when=None) -> str:
    from datetime import datetime

    n = max(1, int(count))
    ts = (when or datetime.now()).strftime("%Y%m%d")
    ext = extension if extension.startswith(".") else f".{extension}" if extension else ".xlsx"
    return f"{n}票进仓单_{ts}{ext}"


def download_dps_warehouse_entry(
    config_path: Path,
    dps_waybill_ids: list[str],
    *,
    warehouse_key: str,
    timeout: int | None = None,
) -> DpsCargoDataFile:
    """
    进仓单：POST/GET + URL ?ids=...；可选 ?warehouseCode=SHENZHEN|YIWU。
    """
    cfg = require_dps_warehouse_entry_download_config(config_path)
    ids = [str(x).strip() for x in dps_waybill_ids if str(x).strip()]
    if not ids:
        raise ValueError("进仓单 waybill id 不能为空")
    if len(ids) > 50:
        raise ValueError("进仓单单次请求 ids 不能超过 50 个")

    extra: dict[str, str] = {}
    param_name = cfg.get("warehouse_query_param") or ""
    wh = (warehouse_key or "").strip().upper()
    if param_name and wh:
        extra[param_name] = wh

    url = build_dps_data_download_url(cfg["url"], ids, extra_query=extra or None)
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
