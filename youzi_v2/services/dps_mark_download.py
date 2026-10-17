"""DPS 唛头下载（URL / Token 仅来自 config.json）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .dps_data_download import DpsCargoDataFile, _parse_binary_response
from .shipment_query_config import load_config_json, resolve_dps_authorization

CONFIG_MARK_KEY = "dps_mark_download"
CONFIG_BATCH_MARK_KEY = "dps_batchmark_download"
DEFAULT_TIMEOUT = 60
DEFAULT_MARK_TYPE = "2"


def _block_config(
    config_path: Path,
    block_key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = load_config_json(config_path)
    raw = config.get(block_key)
    block = raw if isinstance(raw, dict) else {}
    return config, block


def load_dps_mark_download_config(config_path: Path) -> dict[str, Any]:
    config, block = _block_config(config_path, CONFIG_MARK_KEY)
    method = (block.get("method") or "POST").strip().upper()
    if method not in ("GET", "POST"):
        method = "POST"
    mark_type = block.get("type") or block.get("markType") or DEFAULT_MARK_TYPE
    return {
        "url": (block.get("url") or "").strip(),
        "authorization": resolve_dps_authorization(config, block),
        "timeout": int(block.get("timeout") or DEFAULT_TIMEOUT),
        "method": method,
        "mark_type": str(mark_type).strip() or DEFAULT_MARK_TYPE,
    }


def load_dps_batch_mark_download_config(config_path: Path) -> dict[str, Any]:
    config, block = _block_config(config_path, CONFIG_BATCH_MARK_KEY)
    method = (block.get("method") or "POST").strip().upper()
    if method not in ("GET", "POST"):
        method = "POST"
    return {
        "url": (block.get("url") or "").strip(),
        "authorization": resolve_dps_authorization(config, block),
        "timeout": int(block.get("timeout") or DEFAULT_TIMEOUT),
        "method": method,
    }


def require_dps_mark_download_config(config_path: Path) -> dict[str, Any]:
    cfg = load_dps_mark_download_config(config_path)
    if not cfg["url"]:
        raise ValueError(f"config.json 缺少 {CONFIG_MARK_KEY}.url")
    if not cfg["authorization"]:
        raise ValueError("config.json 缺少 dps_authorization（或块内 Authorization）")
    return cfg


def require_dps_batch_mark_download_config(config_path: Path) -> dict[str, Any]:
    cfg = load_dps_batch_mark_download_config(config_path)
    if not cfg["url"]:
        raise ValueError(f"config.json 缺少 {CONFIG_BATCH_MARK_KEY}.url")
    if not cfg["authorization"]:
        raise ValueError("config.json 缺少 dps_authorization（或块内 Authorization）")
    return cfg


def build_dps_mark_download_url(
    base_url: str,
    dps_waybill_id: str,
    *,
    mark_type: str,
) -> str:
    wid = (dps_waybill_id or "").strip()
    if not wid:
        raise ValueError("id 不能为空")
    base = (base_url or "").strip()
    if not base:
        raise ValueError(f"{CONFIG_MARK_KEY}.url 为空")
    mtype = (mark_type or DEFAULT_MARK_TYPE).strip()
    parsed = urlparse(base)
    existing = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k not in ("id", "type")
    ]
    pairs = [*existing, ("id", wid), ("type", mtype)]
    query = urlencode(pairs)
    return urlunparse(parsed._replace(query=query))


def download_dps_single_mark(
    config_path: Path,
    dps_waybill_id: str,
    *,
    timeout: int | None = None,
) -> DpsCargoDataFile:
    """单个唛头：POST/GET + URL ?id=&type=（type 默认 2，可配置）。"""
    cfg = require_dps_mark_download_config(config_path)
    url = build_dps_mark_download_url(
        cfg["url"],
        dps_waybill_id,
        mark_type=cfg["mark_type"],
    )
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


def download_dps_batch_mark(
    config_path: Path,
    dps_waybill_ids: list[str],
    *,
    timeout: int | None = None,
) -> DpsCargoDataFile:
    """多个唛头：POST JSON body 为 id 数组。"""
    cfg = require_dps_batch_mark_download_config(config_path)
    ids = [str(x).strip() for x in dps_waybill_ids if str(x).strip()]
    if not ids:
        raise ValueError("唛头 batch ids 不能为空")
    url = cfg["url"]
    headers = {
        "Authorization": cfg["authorization"],
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    req_timeout = timeout if timeout is not None else cfg["timeout"]
    if cfg["method"] == "GET":
        raise ValueError(f"{CONFIG_BATCH_MARK_KEY} 仅支持 POST")
    resp = requests.post(url, headers=headers, json=ids, timeout=req_timeout)
    resp.raise_for_status()
    return _parse_binary_response(resp)


def safe_mark_filename(stem: str, extension: str) -> str:
    base = (stem or "").strip() or "运单"
    for ch in '\\/:*?"<>|':
        base = base.replace(ch, "_")
    ext = extension if extension.startswith(".") else f".{extension}" if extension else ".pdf"
    return f"{base}_mark{ext}"
