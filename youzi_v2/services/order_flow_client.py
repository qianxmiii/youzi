"""订单流转远端拉取。地址和鉴权只读 config.json，不写进代码。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .shipment_query_config import _normalize_dps_authorization, load_config_json

AUTH_KEY = "dps_ddlz_authorization"
ORDERS_KEY = "dps_ddlz_getOrders"
_MAX_PAGES = 40


def load_order_flow_config(config_path: Path, config_key: str = ORDERS_KEY) -> dict[str, Any]:
    config = load_config_json(config_path)
    block = config.get(config_key)
    if not isinstance(block, dict):
        block = {}
    raw_auth = config.get(AUTH_KEY) or block.get("Authorization") or block.get("authorization")
    auth = _normalize_dps_authorization(raw_auth if isinstance(raw_auth, str) else "")
    page_size = block.get("pageSize") or block.get("page_size") or 50
    try:
        page_size = max(1, min(int(page_size), 200))
    except (TypeError, ValueError):
        page_size = 50
    timeout = block.get("timeout") or 30
    try:
        timeout = max(5, int(timeout))
    except (TypeError, ValueError):
        timeout = 30
    return {
        "url": str(block.get("url") or "").strip(),
        "authorization": auth,
        "method": str(block.get("method") or "GET").strip().upper() or "GET",
        "page_size": page_size,
        "timeout": timeout,
    }


def require_order_flow_config(config_path: Path, config_key: str = ORDERS_KEY) -> dict[str, Any]:
    cfg = load_order_flow_config(config_path, config_key)
    if not cfg["url"]:
        raise ValueError(f"config.json 缺少 {config_key}.url")
    if not cfg["authorization"]:
        raise ValueError(f"config.json 缺少 {AUTH_KEY}")
    return cfg


def build_orders_page_url(base_url: str, page_num: int, page_size: int) -> str:
    parsed = urlparse(base_url)
    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"pageNum", "pageSize"}
    ]
    query = urlencode([*kept, ("pageNum", str(page_num)), ("pageSize", str(page_size))])
    return urlunparse(parsed._replace(query=query))


def parse_orders_page(body: Any) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(body, dict):
        raise ValueError("订单流转响应不是 JSON 对象")
    code = body.get("code")
    if code not in (200, "200", 0, "0"):
        raise ValueError(body.get("msg") or f"订单流转查询失败 code={code}")
    rows = body.get("rows")
    if not isinstance(rows, list):
        raise ValueError("订单流转 rows 不是数组")
    if any(not isinstance(row, dict) or not str(row.get("waybillNo") or "").strip() for row in rows):
        raise ValueError("订单流转包含无效订单，保留原快照")
    clean = rows
    total_raw = body.get("total")
    try:
        total = int(total_raw)
    except (TypeError, ValueError):
        raise ValueError("订单流转缺少有效 total，保留原快照")
    if total < 0:
        raise ValueError("订单流转 total 无效")
    return clean, total


def fetch_order_flow_rows(config_path: Path, config_key: str = ORDERS_KEY) -> list[dict[str, Any]]:
    cfg = require_order_flow_config(config_path, config_key)
    headers = {"Authorization": cfg["authorization"], "Accept": "application/json"}
    collected: list[dict[str, Any]] = []
    seen: set[str] = set()
    total = 0
    for page_num in range(1, _MAX_PAGES + 1):
        url = build_orders_page_url(cfg["url"], page_num, cfg["page_size"])
        try:
            resp = requests.request(
                cfg["method"],
                url,
                headers=headers,
                timeout=cfg["timeout"],
            )
        except requests.RequestException as exc:
            raise ValueError(f"订单流转请求失败：{exc}") from exc
        if resp.status_code >= 400:
            raise ValueError(f"订单流转请求失败 HTTP {resp.status_code}")
        try:
            body = resp.json()
        except ValueError as exc:
            raise ValueError("订单流转响应不是 JSON") from exc
        rows, total = parse_orders_page(body)
        added = 0
        for row in rows:
            key = str(row.get("waybillNo") or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            collected.append(row)
            added += 1
        if len(collected) == total:
            return collected
        if not rows or added == 0 or len(collected) > total:
            raise ValueError("订单流转分页不完整，保留原快照")
    raise ValueError("订单流转超过分页上限，保留原快照")
