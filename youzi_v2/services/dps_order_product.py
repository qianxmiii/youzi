"""DPS 运单产品查询（URL / Token 仅来自 config.json）。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .shipment_query_config import (
    QUERY_BY_ORDER_KEY,
    load_config_json,
    resolve_dps_authorization,
)

CONFIG_KEY = "dps_getOrderProduct"
DEFAULT_TIMEOUT = 30
_WAYBILL_ID_PARAM = "commerceWaybillId"


def load_order_product_config(config_path: Path) -> dict[str, Any]:
    """读取 config.json → dps_getOrderProduct。url 必填；Authorization 缺省用根级 dps_authorization。"""
    config = load_config_json(config_path)
    block = config.get(CONFIG_KEY)
    if not isinstance(block, dict):
        block = {}
    order = config.get(QUERY_BY_ORDER_KEY)
    order_block = order if isinstance(order, dict) else {}
    method = str(block.get("method") or "GET").strip().upper() or "GET"
    return {
        "url": (block.get("url") or "").strip(),
        "authorization": resolve_dps_authorization(config, block, order_block),
        "timeout": int(block.get("timeout") or DEFAULT_TIMEOUT),
        "method": method,
    }


def require_order_product_config(config_path: Path) -> dict[str, Any]:
    cfg = load_order_product_config(config_path)
    if not cfg["url"]:
        raise ValueError(f"config.json 缺少 {CONFIG_KEY}.url")
    if not cfg["authorization"]:
        raise ValueError("config.json 缺少 dps_authorization（或块内 Authorization）")
    return cfg


def build_order_product_url(base_url: str, commerce_waybill_id: str) -> str:
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
    query = urlencode([*existing, (_WAYBILL_ID_PARAM, wid)])
    return urlunparse(parsed._replace(query=query))


def parse_order_product_body(body: Any) -> list[dict[str, Any]]:
    """只保留中文品名、英文品名、箱数。"""
    if not isinstance(body, dict):
        raise ValueError("DPS 运单产品响应格式无效")
    code = body.get("code")
    if code not in (200, "200", 0, "0"):
        raise ValueError(body.get("msg") or f"DPS 运单产品失败 code={code}")
    data = body.get("data")
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError("DPS 运单产品 data 须为数组")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ctns = _parse_ctns(item.get("ctns"))
        rows.append(
            {
                "cnName": str(item.get("cnName") or "").strip(),
                "enName": str(item.get("enName") or "").strip(),
                "ctns": ctns,
            }
        )
    return rows


def _parse_ctns(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def sum_product_ctns(products: list[dict[str, Any]]) -> int | None:
    numbers = [item["ctns"] for item in products if isinstance(item.get("ctns"), int)]
    if not numbers:
        return None
    return sum(numbers)


def classify_product_ctns(
    shipment_ctns: int | None,
    product_ctns: int | None,
) -> tuple[str, int | None, str]:
    """返回 (kind, diff, message)。kind 为 match、mismatch、error。"""
    if shipment_ctns is None and product_ctns is None:
        return "error", None, "运单件数和产品箱数都为空"
    if shipment_ctns is None:
        return "error", None, "运单件数为空"
    if product_ctns is None:
        return "error", None, "产品箱数为空"
    diff = product_ctns - shipment_ctns
    if diff == 0:
        return "match", 0, ""
    return "mismatch", diff, ""


MAX_PRODUCT_CTNS_CHECK = 50


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def check_shipment_product_ctns(
    repo: Any,
    config_path: Path,
    shipment_ids: list[str],
) -> dict[str, Any]:
    """逐票比较产品箱数合计与运单件数。一致的只计数，问题票保留明细。"""
    ids: list[str] = []
    seen: set[str] = set()
    for raw in shipment_ids:
        sid = str(raw or "").strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        ids.append(sid)
    if not ids:
        raise ValueError("请选择运单")
    if len(ids) > MAX_PRODUCT_CTNS_CHECK:
        raise ValueError(f"单次最多核对 {MAX_PRODUCT_CTNS_CHECK} 票")

    matched = 0
    issues: list[dict[str, Any]] = []
    for sid in ids:
        row = repo.get_by_id(sid)
        if row is None:
            issues.append(_issue(sid, sid, None, None, "error", "运单不存在"))
            continue
        shipment_no = str(row.get("shipmentNo") or "").strip() or sid
        shipment_ctns = _as_int(row.get("ctns"))
        waybill_id = str(row.get("waybillId") or "").strip()
        if not waybill_id:
            issues.append(
                _issue(sid, shipment_no, shipment_ctns, None, "error", "无 DPS 运单 ID，请先更新运单")
            )
            continue
        try:
            products = query_order_products(config_path, waybill_id)
        except ValueError as exc:
            issues.append(_issue(sid, shipment_no, shipment_ctns, None, "error", str(exc)))
            continue
        if not products:
            issues.append(_issue(sid, shipment_no, shipment_ctns, None, "error", "没有产品"))
            continue
        product_ctns = sum_product_ctns(products)
        kind, diff, message = classify_product_ctns(shipment_ctns, product_ctns)
        if kind == "match":
            matched += 1
            continue
        issues.append(_issue(sid, shipment_no, shipment_ctns, product_ctns, kind, message, diff))
    return {"matched": matched, "checked": len(ids), "issues": issues}


def _issue(
    shipment_id: str,
    shipment_no: str,
    shipment_ctns: int | None,
    product_ctns: int | None,
    kind: str,
    message: str,
    diff: int | None = None,
) -> dict[str, Any]:
    return {
        "id": shipment_id,
        "shipmentNo": shipment_no,
        "shipmentCtns": shipment_ctns,
        "productCtns": product_ctns,
        "diff": diff,
        "kind": kind,
        "message": message,
    }


def query_order_products(
    config_path: Path,
    commerce_waybill_id: str,
    *,
    timeout: int | None = None,
) -> list[dict[str, Any]]:
    """按 commerceWaybillId 查询运单产品。"""
    cfg = require_order_product_config(config_path)
    url = build_order_product_url(cfg["url"], commerce_waybill_id)
    headers = {
        "Authorization": cfg["authorization"],
        "Accept": "application/json",
    }
    method = cfg["method"]
    try:
        resp = requests.request(
            method,
            url,
            headers=headers,
            timeout=timeout if timeout is not None else cfg["timeout"],
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(f"获取运单产品失败：{exc}") from exc
    try:
        body = resp.json()
    except ValueError as exc:
        raise ValueError("DPS 运单产品响应不是 JSON") from exc
    return parse_order_product_body(body)


def query_export_product_names(config_path: Path, waybill_ids: list[str]) -> dict[str, str]:
    """从查看产品使用的接口取品名，分别按语言去重。"""
    if not waybill_ids:
        return {}

    def names_for(waybill_id: str) -> str:
        products = query_order_products(config_path, waybill_id)
        lines = []
        for field in ("cnName", "enName"):
            names = (product[field].strip() for product in products)
            line = ",".join(dict.fromkeys(name for name in names if name))
            if line:
                lines.append(line)
        return "\n".join(lines)

    names_by_id = {}
    batch_size = 4
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        for start in range(0, len(waybill_ids), batch_size):
            batch = waybill_ids[start:start + batch_size]
            names_by_id.update(zip(batch, executor.map(names_for, batch)))
    return names_by_id
