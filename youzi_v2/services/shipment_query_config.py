"""运单查询 API：config/config.json 的 shipment_queryByPerson / shipment_queryByOrder。"""

from __future__ import annotations

import json
import math
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import requests

from ..db.datetime_util import DATETIME_FMT

QUERY_BY_PERSON_KEY = "shipment_queryByPerson"
QUERY_BY_ORDER_KEY = "shipment_queryByOrder"
QUERY_PARAM = "odds"
PAGE_NUM_PARAM = "pageNum"
TRANSIT_TIME_START_PARAM = "transitTimeStart"
TRANSIT_TIME_END_PARAM = "transitTimeEnd"
DEFAULT_PAGE_SIZE = 10
DEFAULT_TIMEOUT = 30
MAX_PAGES = 500

ShipmentQueryMode = Literal["by_person", "by_order"]


def _read_auth(block: dict[str, Any]) -> str:
    return (
        block.get("Authorization")
        or block.get("authorization")
        or ""
    ).strip()


def _page_size_from_block(block: dict[str, Any], url: str) -> int:
    raw = block.get("pageSize") or block.get("page_size")
    if raw is not None:
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            pass
    parsed = urlparse(url)
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() == "pagesize":
            try:
                return max(1, int(value))
            except (TypeError, ValueError):
                break
    return DEFAULT_PAGE_SIZE


def _load_query_block(config_path: Path, block_key: str) -> dict[str, Any]:
    if not config_path.is_file():
        raise FileNotFoundError(f"未找到配置文件：{config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        config: dict[str, Any] = json.load(f)
    block = config.get(block_key)
    if not isinstance(block, dict):
        return {"url": "", "authorization": "", "pageSize": DEFAULT_PAGE_SIZE}
    url = (block.get("url") or "").strip()
    return {
        "url": url,
        "authorization": _read_auth(block),
        "pageSize": _page_size_from_block(block, url),
    }


def load_shipment_query_by_person_config(config_path: Path) -> dict[str, Any]:
    """查询全部运单（按销售助理等条件，url 内已带筛选参数）。"""
    return _load_query_block(config_path, QUERY_BY_PERSON_KEY)


def load_shipment_query_by_order_config(config_path: Path) -> dict[str, Any]:
    """按运单号查询（拼接 odds）。"""
    return _load_query_block(config_path, QUERY_BY_ORDER_KEY)


def require_shipment_query_by_person_config(config_path: Path) -> dict[str, Any]:
    cfg = load_shipment_query_by_person_config(config_path)
    if not cfg["url"]:
        raise ValueError(f"config.json 的 {QUERY_BY_PERSON_KEY}.url 未配置")
    return cfg


def require_shipment_query_by_order_config(config_path: Path) -> dict[str, Any]:
    cfg = load_shipment_query_by_order_config(config_path)
    if not cfg["url"]:
        raise ValueError(f"config.json 的 {QUERY_BY_ORDER_KEY}.url 未配置")
    return cfg


# 兼容旧名
load_shipment_query_config = load_shipment_query_by_order_config
require_shipment_query_config = require_shipment_query_by_order_config


def normalize_shipment_nos(shipment_nos: list[str] | str | None) -> list[str]:
    """去重、去空；支持单个字符串或列表。"""
    if shipment_nos is None:
        return []
    if isinstance(shipment_nos, str):
        raw = [shipment_nos]
    else:
        raw = list(shipment_nos)
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        for part in str(item).replace("\n", ",").split(","):
            sn = part.strip()
            if not sn or sn in seen:
                continue
            seen.add(sn)
            out.append(sn)
    return out


def _strip_query_keys(pairs: list[tuple[str, str]], *keys: str) -> list[tuple[str, str]]:
    drop = {k.lower() for k in keys}
    return [(k, v) for k, v in pairs if k.lower() not in drop]


def default_transit_time_range(
    now: datetime | None = None,
) -> tuple[str, str]:
    """当月发运时间范围：首日 00:00:00 至末日 23:59:59。"""
    ref = now or datetime.now()
    start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = monthrange(ref.year, ref.month)[1]
    end = ref.replace(
        day=last_day, hour=23, minute=59, second=59, microsecond=0
    )
    return start.strftime(DATETIME_FMT), end.strftime(DATETIME_FMT)


def resolve_transit_time_range(
    transit_time_start: str | None = None,
    transit_time_end: str | None = None,
    *,
    now: datetime | None = None,
) -> tuple[str, str]:
    """空值时使用当月默认范围。"""
    default_start, default_end = default_transit_time_range(now)
    start = (transit_time_start or "").strip() or default_start
    end = (transit_time_end or "").strip() or default_end
    return start, end


def build_shipment_query_by_person_url(
    base_url: str,
    *,
    page_num: int = 1,
    transit_time_start: str | None = None,
    transit_time_end: str | None = None,
) -> str:
    """全部运单列表：注入 pageNum、transitTimeStart、transitTimeEnd。"""
    base = (base_url or "").strip()
    if not base:
        raise ValueError(f"{QUERY_BY_PERSON_KEY}.url 为空")
    if page_num < 1:
        raise ValueError("pageNum 须 >= 1")

    start, end = resolve_transit_time_range(transit_time_start, transit_time_end)
    parsed = urlparse(base)
    existing = _strip_query_keys(
        parse_qsl(parsed.query, keep_blank_values=True),
        PAGE_NUM_PARAM,
        TRANSIT_TIME_START_PARAM,
        TRANSIT_TIME_END_PARAM,
        "orderTimeStart",
        "orderTimeEnd",
    )
    pairs = [
        *existing,
        (TRANSIT_TIME_START_PARAM, start),
        (TRANSIT_TIME_END_PARAM, end),
        (PAGE_NUM_PARAM, str(page_num)),
    ]
    query = urlencode(pairs, quote_via=quote)
    return urlunparse(parsed._replace(query=query))


def build_shipment_query_by_order_url(
    base_url: str,
    shipment_nos: list[str] | str,
    *,
    page_num: int = 1,
) -> str:
    """按运单号查询：拼接 odds（空格 → %20）与 pageNum。"""
    base = (base_url or "").strip()
    if not base:
        raise ValueError(f"{QUERY_BY_ORDER_KEY}.url 为空")
    nos = normalize_shipment_nos(shipment_nos)
    if not nos:
        raise ValueError("至少需要一个运单号")
    if page_num < 1:
        raise ValueError("pageNum 须 >= 1")

    parsed = urlparse(base)
    existing = _strip_query_keys(
        parse_qsl(parsed.query, keep_blank_values=True),
        PAGE_NUM_PARAM,
        QUERY_PARAM,
    )
    pairs = [
        *existing,
        (QUERY_PARAM, " ".join(nos)),
        (PAGE_NUM_PARAM, str(page_num)),
    ]
    query = urlencode(pairs, quote_via=quote)
    return urlunparse(parsed._replace(query=query))


# 兼容旧名
build_shipment_query_url = build_shipment_query_by_order_url


def parse_shipment_query_response(data: Any) -> dict[str, Any]:
    """解析 { code, msg, total, rows }，行内单号字段 odd。"""
    if not isinstance(data, dict):
        raise ValueError("运单查询返回不是 JSON 对象")
    code_raw = data.get("code")
    try:
        code = int(code_raw) if code_raw is not None else 0
    except (TypeError, ValueError):
        code = 0
    rows = data.get("rows")
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        raise ValueError("运单查询 rows 不是数组")
    total_raw = data.get("total")
    try:
        total = int(total_raw) if total_raw is not None else len(rows)
    except (TypeError, ValueError):
        total = len(rows)
    return {
        "code": code,
        "msg": str(data.get("msg") or ""),
        "total": max(0, total),
        "rows": rows,
    }


def shipment_odd(row: dict[str, Any]) -> str:
    return str(row.get("odd") or row.get("shipmentNo") or "").strip()


def _request_shipment_query_url(
    url: str,
    authorization: str,
    *,
    timeout: int,
) -> tuple[Any, str | None]:
    headers: dict[str, str] = {}
    if authorization:
        headers["Authorization"] = authorization
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        try:
            return resp.json(), None
        except ValueError:
            return resp.text, None
    except Exception as exc:
        return None, str(exc)


def _fetch_page(
    url: str,
    authorization: str,
    *,
    timeout: int,
) -> tuple[dict[str, Any] | None, str | None]:
    data, err = _request_shipment_query_url(url, authorization, timeout=timeout)
    if err:
        return None, err
    if not isinstance(data, dict):
        return None, "运单查询返回不是 JSON 对象"
    parsed = parse_shipment_query_response(data)
    if parsed["code"] != 200:
        return parsed, parsed["msg"] or f"查询失败 code={parsed['code']}"
    return parsed, None


def query_shipments_by_person_page(
    config_path: Path,
    *,
    page_num: int = 1,
    transit_time_start: str | None = None,
    transit_time_end: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any] | None, str | None]:
    """查询全部运单（单页）。"""
    cfg = require_shipment_query_by_person_config(config_path)
    url = build_shipment_query_by_person_url(
        cfg["url"],
        page_num=page_num,
        transit_time_start=transit_time_start,
        transit_time_end=transit_time_end,
    )
    return _fetch_page(url, cfg["authorization"], timeout=timeout)


def query_shipments_by_order_page(
    shipment_nos: list[str] | str,
    config_path: Path,
    *,
    page_num: int = 1,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any] | None, str | None]:
    """按运单号查询（单页）。"""
    cfg = require_shipment_query_by_order_config(config_path)
    url = build_shipment_query_by_order_url(
        cfg["url"], shipment_nos, page_num=page_num
    )
    return _fetch_page(url, cfg["authorization"], timeout=timeout)


def _query_all_pages(
    *,
    page_size: int,
    fetch_page: Callable[[int], tuple[dict[str, Any] | None, str | None]],
) -> tuple[dict[str, Any] | None, str | None]:
    all_rows: list[dict[str, Any]] = []
    total = 0
    msg = ""
    code = 0
    pages_fetched = 0
    expected_pages = 1

    for page_num in range(1, MAX_PAGES + 1):
        if page_num > expected_pages:
            break
        parsed, err = fetch_page(page_num)
        if err:
            return None, err
        assert parsed is not None
        code = int(parsed["code"])
        msg = str(parsed["msg"])
        total = int(parsed["total"])
        page_rows = list(parsed["rows"])
        all_rows.extend(page_rows)
        pages_fetched = page_num
        expected_pages = max(1, math.ceil(total / page_size)) if total else 1
        if not page_rows or len(all_rows) >= total:
            break

    return {
        "code": code,
        "msg": msg,
        "total": total,
        "rows": all_rows,
        "pages": pages_fetched,
    }, None


def query_shipments_by_person(
    config_path: Path,
    *,
    transit_time_start: str | None = None,
    transit_time_end: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any] | None, str | None]:
    """查询全部运单，按 total 自动翻页。"""
    cfg = require_shipment_query_by_person_config(config_path)
    page_size = int(cfg.get("pageSize") or DEFAULT_PAGE_SIZE)
    start, end = resolve_transit_time_range(transit_time_start, transit_time_end)

    def fetch_page(page_num: int) -> tuple[dict[str, Any] | None, str | None]:
        return query_shipments_by_person_page(
            config_path,
            page_num=page_num,
            transit_time_start=start,
            transit_time_end=end,
            timeout=timeout,
        )

    result, err = _query_all_pages(page_size=page_size, fetch_page=fetch_page)
    if result is not None:
        result["transitTimeStart"] = start
        result["transitTimeEnd"] = end
    return result, err


def query_shipments_by_order(
    shipment_nos: list[str] | str,
    config_path: Path,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any] | None, str | None]:
    """按运单号查询，按 total 自动翻页。"""
    cfg = require_shipment_query_by_order_config(config_path)
    page_size = int(cfg.get("pageSize") or DEFAULT_PAGE_SIZE)

    def fetch_page(page_num: int) -> tuple[dict[str, Any] | None, str | None]:
        return query_shipments_by_order_page(
            shipment_nos, config_path, page_num=page_num, timeout=timeout
        )

    return _query_all_pages(page_size=page_size, fetch_page=fetch_page)


# 兼容旧名
default_order_time_range = default_transit_time_range
resolve_order_time_range = resolve_transit_time_range
ORDER_TIME_START_PARAM = TRANSIT_TIME_START_PARAM
ORDER_TIME_END_PARAM = TRANSIT_TIME_END_PARAM
query_shipments = query_shipments_by_order
query_shipments_page = query_shipments_by_order_page


def query_shipments_raw(
    shipment_nos: list[str] | str,
    config_path: Path,
    *,
    page_num: int = 1,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[Any, str | None]:
    cfg = require_shipment_query_by_order_config(config_path)
    url = build_shipment_query_by_order_url(
        cfg["url"], shipment_nos, page_num=page_num
    )
    return _request_shipment_query_url(url, cfg["authorization"], timeout=timeout)
