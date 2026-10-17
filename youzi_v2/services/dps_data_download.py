"""DPS 货箱重量尺寸数据下载（URL / Token 仅来自 config.json）。"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .shipment_query_config import load_config_json, resolve_dps_authorization

CONFIG_KEY = "dps_data_download"
DEFAULT_TIMEOUT = 60
_IDS_PARAM = "ids"


@dataclass(frozen=True)
class DpsCargoDataFile:
    content: bytes
    media_type: str
    extension: str  # 含点，如 .xlsx
    filename: str | None = None  # Content-Disposition / JSON 中的原始文件名


def load_dps_data_download_config(config_path: Path) -> dict[str, Any]:
    """
    读取货箱数据下载配置（config.json → dps_data_download）。
    - url：必填，完整接口地址（勿写入业务代码）
    - Authorization：可省略，缺省使用 config 根级 dps_authorization
    - method：可选 POST（默认）或 GET
    """
    config = load_config_json(config_path)

    block = config.get(CONFIG_KEY)
    if not isinstance(block, dict):
        block = {}

    method = (block.get("method") or "POST").strip().upper()
    if method not in ("GET", "POST"):
        method = "POST"

    ids_post_format = (
        block.get("idsPostFormat") or block.get("ids_post_format") or "query"
    )
    ids_post_format = str(ids_post_format).strip().lower()
    if ids_post_format not in ("query", "array", "string"):
        ids_post_format = "query"

    return {
        "url": (block.get("url") or "").strip(),
        "authorization": resolve_dps_authorization(config, block),
        "timeout": int(block.get("timeout") or DEFAULT_TIMEOUT),
        "method": method,
        "ids_post_format": ids_post_format,
    }


def require_dps_data_download_config(config_path: Path) -> dict[str, Any]:
    cfg = load_dps_data_download_config(config_path)
    if not cfg["url"]:
        raise ValueError(f"config.json 缺少 {CONFIG_KEY}.url")
    if not cfg["authorization"]:
        raise ValueError("config.json 缺少 dps_authorization（或块内 Authorization）")
    return cfg


def _normalize_dps_waybill_ids(dps_waybill_ids: str | list[str]) -> list[str]:
    if isinstance(dps_waybill_ids, str):
        raw = dps_waybill_ids.replace("，", ",")
        parts = [p.strip() for p in raw.split(",") if p.strip()]
    else:
        parts = [str(p).strip() for p in dps_waybill_ids if str(p).strip()]
    return parts


def build_dps_data_download_url(base_url: str, dps_waybill_ids: str | list[str]) -> str:
    """在配置 URL 上设置查询参数 ids（多个 DPS id 用英文逗号拼接）。"""
    parts = _normalize_dps_waybill_ids(dps_waybill_ids)
    if not parts:
        raise ValueError("ids 不能为空")
    ids_value = ",".join(parts)
    base = (base_url or "").strip()
    if not base:
        raise ValueError(f"{CONFIG_KEY}.url 为空")
    parsed = urlparse(base)
    existing = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k != _IDS_PARAM
    ]
    pairs = [*existing, (_IDS_PARAM, ids_value)]
    query = urlencode(pairs)
    return urlunparse(parsed._replace(query=query))


def _extension_from_content_type(content_type: str) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    mapping = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
        "text/csv": ".csv",
        "application/zip": ".zip",
        "application/pdf": ".pdf",
    }
    return mapping.get(ct, "")


def _filename_from_disposition(disposition: str | None) -> str:
    if not disposition:
        return ""
    from urllib.parse import unquote

    match = re.search(r"filename\*=UTF-8''([^;]+)", disposition, re.I)
    if match:
        return unquote(match.group(1).strip())
    quoted = re.search(r'filename="([^"]+)"', disposition, re.I)
    if quoted:
        return quoted.group(1).strip()
    plain = re.search(r"filename=([^;\n]+)", disposition, re.I)
    if plain:
        return plain.group(1).strip().strip('"')
    return ""


def _extension_from_disposition(disposition: str | None) -> str:
    name = _filename_from_disposition(disposition)
    if not name or "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1].lower()


def sanitize_dps_download_filename(name: str) -> str:
    """保留 DPS 原名，仅去掉路径与非法字符。"""
    base = Path(name.strip()).name
    for ch in '\\/:*?"<>|':
        base = base.replace(ch, "_")
    return base.strip()


def resolve_dps_download_filename(
    file: DpsCargoDataFile,
    *,
    fallback: str,
) -> str:
    if file.filename and file.filename.strip():
        safe = sanitize_dps_download_filename(file.filename)
        if safe:
            return safe
    return fallback


def _decode_json_payload(body: dict[str, Any]) -> DpsCargoDataFile:
    code = body.get("code")
    if code not in (200, "200", 0, "0"):
        raise ValueError(body.get("msg") or f"DPS 货箱数据失败 code={code}")

    data = body.get("data")
    if isinstance(data, str) and data.strip():
        try:
            raw = base64.b64decode(data, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("DPS 货箱数据 data 不是有效的 base64") from exc
        return DpsCargoDataFile(raw, "application/octet-stream", ".xlsx", None)

    if isinstance(data, dict):
        b64 = data.get("content") or data.get("fileContent") or data.get("base64")
        if isinstance(b64, str) and b64.strip():
            raw = base64.b64decode(b64, validate=True)
            ext = ""
            fname_raw = data.get("fileName") or data.get("filename")
            fname: str | None = None
            if isinstance(fname_raw, str) and fname_raw.strip():
                fname = fname_raw.strip()
                if "." in fname:
                    ext = "." + fname.rsplit(".", 1)[-1].lower()
            return DpsCargoDataFile(
                raw,
                "application/octet-stream",
                ext or ".xlsx",
                fname,
            )
        file_url = data.get("url") or data.get("fileUrl")
        if isinstance(file_url, str) and file_url.strip():
            return _fetch_binary_url(file_url.strip())

    raise ValueError("DPS 货箱数据响应缺少可下载内容")


def _fetch_binary_url(url: str, *, authorization: str = "") -> DpsCargoDataFile:
    headers: dict[str, str] = {"Accept": "*/*"}
    if authorization:
        headers["Authorization"] = authorization
    resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return _parse_binary_response(resp)


def _parse_binary_response(resp: requests.Response) -> DpsCargoDataFile:
    ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    disposition = resp.headers.get("Content-Disposition")

    if ctype in ("application/json", "text/json") or (
        resp.content[:1] == b"{" and b'"code"' in resp.content[:200]
    ):
        try:
            body = resp.json()
        except ValueError as exc:
            raise ValueError("DPS 货箱数据 JSON 响应无效") from exc
        if not isinstance(body, dict):
            raise ValueError("DPS 货箱数据 JSON 响应须为对象")
        return _decode_json_payload(body)

    fname = _filename_from_disposition(disposition) or None
    ext = (
        _extension_from_disposition(disposition)
        or _extension_from_content_type(ctype)
        or (".xlsx" if resp.content[:2] == b"PK" else "")
        or ".xlsx"
    )
    media = ctype or "application/octet-stream"
    return DpsCargoDataFile(resp.content, media, ext, fname)


def _post_body_for_ids(cfg: dict[str, Any], dps_waybill_ids: str | list[str]) -> dict[str, Any]:
    parts = _normalize_dps_waybill_ids(dps_waybill_ids)
    joined = ",".join(parts)
    if cfg.get("ids_post_format") == "string":
        return {_IDS_PARAM: joined}
    return {_IDS_PARAM: parts}


def download_dps_cargo_data(
    config_path: Path,
    dps_waybill_ids: str | list[str],
    *,
    timeout: int | None = None,
) -> DpsCargoDataFile:
    """按 DPS 运单 id（waybill_id，多个逗号分隔）下载货箱重量尺寸。"""
    cfg = require_dps_data_download_config(config_path)
    parts = _normalize_dps_waybill_ids(dps_waybill_ids)
    if not parts:
        raise ValueError("ids 不能为空")
    headers = {
        "Authorization": cfg["authorization"],
        "Accept": "*/*",
    }
    req_timeout = timeout if timeout is not None else cfg["timeout"]
    method = cfg["method"]
    if method == "POST":
        if cfg.get("ids_post_format") == "query":
            # 与 DPS exportBox 一致：POST + URL ?ids=waybillId，无 JSON body
            url = build_dps_data_download_url(cfg["url"], parts)
            resp = requests.post(url, headers=headers, timeout=req_timeout)
        else:
            url = (cfg["url"] or "").strip()
            if not url:
                raise ValueError(f"{CONFIG_KEY}.url 为空")
            headers["Content-Type"] = "application/json"
            resp = requests.post(
                url,
                headers=headers,
                json=_post_body_for_ids(cfg, parts),
                timeout=req_timeout,
            )
    else:
        url = build_dps_data_download_url(cfg["url"], parts)
        resp = requests.get(url, headers=headers, timeout=req_timeout)
    resp.raise_for_status()
    return _parse_binary_response(resp)


def safe_cargo_data_filename(stem: str, extension: str) -> str:
    """{单号}_data{ext}，去除非法文件名字符。"""
    base = (stem or "").strip() or "运单"
    for ch in '\\/:*?"<>|':
        base = base.replace(ch, "_")
    ext = extension if extension.startswith(".") else f".{extension}" if extension else ".xlsx"
    return f"{base}_data{ext}"
