"""DPS 运单明细状态轨迹查询（URL / Token 仅来自 config.json）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .shipment_query_config import (
    QUERY_BY_ORDER_KEY,
    load_config_json,
    resolve_dps_authorization,
)

CONFIG_KEY = "dps_route_status_query"
DEFAULT_TIMEOUT = 30
# 查询参数名与 DPS 约定一致；完整请求 URL 只允许出现在 config.json
_WAYBILL_ID_PARAM = "commerceWaybillId"


def load_waybill_route_info_config(config_path: Path) -> dict[str, Any]:
    """
    读取明细状态轨迹查询配置（config.json → dps_route_status_query）。
    - url：必填，完整接口地址（勿写入业务代码）
    - Authorization：可省略，缺省使用 config 根级 dps_authorization
    """
    config = load_config_json(config_path)

    block = config.get(CONFIG_KEY)
    if not isinstance(block, dict):
        block = {}

    order = config.get(QUERY_BY_ORDER_KEY)
    order_block = order if isinstance(order, dict) else {}

    return {
        "url": (block.get("url") or "").strip(),
        "authorization": resolve_dps_authorization(config, block, order_block),
        "timeout": int(block.get("timeout") or DEFAULT_TIMEOUT),
    }


def require_waybill_route_info_config(config_path: Path) -> dict[str, Any]:
    cfg = load_waybill_route_info_config(config_path)
    if not cfg["url"]:
        raise ValueError(f"config.json 缺少 {CONFIG_KEY}.url")
    if not cfg["authorization"]:
        raise ValueError("config.json 缺少 dps_authorization（或块内 Authorization）")
    return cfg


def build_waybill_route_info_url(base_url: str, commerce_waybill_id: str) -> str:
    wid = (commerce_waybill_id or "").strip()
    if not wid:
        raise ValueError("commerceWaybillId 不能为空")
    base = (base_url or "").strip()
    if not base:
        raise ValueError(f"{CONFIG_KEY}.url 为空")
    parsed = urlparse(base)
    existing = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k != _WAYBILL_ID_PARAM
    ]
    pairs = [*existing, (_WAYBILL_ID_PARAM, wid)]
    query = urlencode(pairs)
    return urlunparse(parsed._replace(query=query))


def query_waybill_route_info(
    config_path: Path,
    commerce_waybill_id: str,
    *,
    timeout: int | None = None,
) -> list[dict[str, Any]]:
    """请求明细状态轨迹列表，返回 data[]（节点列表，可能为空）。"""
    cfg = require_waybill_route_info_config(config_path)
    url = build_waybill_route_info_url(cfg["url"], commerce_waybill_id)
    headers = {
        "Authorization": cfg["authorization"],
        "Accept": "application/json",
    }
    resp = requests.get(
        url,
        headers=headers,
        timeout=timeout if timeout is not None else cfg["timeout"],
    )
    resp.raise_for_status()
    body = resp.json()
    if not isinstance(body, dict):
        raise ValueError("DPS 明细状态轨迹响应格式无效")
    code = body.get("code")
    if code not in (200, "200"):
        raise ValueError(body.get("msg") or f"DPS 明细状态轨迹失败 code={code}")
    data = body.get("data")
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError("DPS 明细状态轨迹 data 须为数组")
    return [x for x in data if isinstance(x, dict)]
