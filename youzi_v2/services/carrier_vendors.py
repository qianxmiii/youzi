"""承运商大类 API：从 config.json vendors 拉取轨迹。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import requests

from ..db.datetime_util import normalize_tracking_time

BATCH_SIZE = 10
DEFAULT_TIMEOUT = 30

LogFn = Callable[[str], None]

# (轨迹列表, 错误, carrier_id, 尾程单号 tracking_number)
CarrierFetch = tuple[list[tuple[str, str]], str | None, str | None, str | None]


def _carrier_ok(
    logs: list[tuple[str, str]],
    carrier_id: str | None = None,
    tracking_number: str | None = None,
) -> CarrierFetch:
    cid = (carrier_id or "").strip() or None
    tn = (tracking_number or "").strip() or None
    return logs, None, cid, tn


def _carrier_fail(msg: str) -> CarrierFetch:
    return [], msg, None, None


def _extract_carrier_id(data: dict[str, Any]) -> str:
    """NextSLS shipment_id、拓普达 jobNum、华威尔 orderno 等。"""
    if not isinstance(data, dict):
        return ""
    for key in ("shipment_id", "jobNum", "orderno", "order_no", "billNo"):
        v = (data.get(key) or "").strip()
        if v:
            return v
    return ""


def _extract_outer_tracking_number(data: dict[str, Any]) -> str:
    """NextSLS outer_carrier_tracking_number 等（UPS/FedEx 尾程单号）。"""
    if not isinstance(data, dict):
        return ""
    for key in (
        "outer_carrier_tracking_number",
        "outerCarrierTrackingNumber",
        "express_tracking_number",
        "expressTrackingNumber",
        "expressNo",
        "expressMainNo",
        "last_mile_tracking_number",
    ):
        v = (data.get(key) or "").strip()
        if v:
            return v
    return ""


_TOPDA_NODE_LABELS: dict[str, str] = {
    "Booked": "已订舱",
    "pickup": "已提货",
    "atd": "已开船",
    "arrivedPod": "已到港",
    "transferOut": "已转出",
    "Deliveried": "已签收",
    "wmsIn": "已入仓",
}


def load_vendors_config(config_path: Path) -> list[dict[str, Any]]:
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    vendors = config.get("vendors")
    if not isinstance(vendors, list):
        raise ValueError("config.json 缺少 vendors 数组")
    return vendors


def detect_platform(vendor: dict[str, Any]) -> str | None:
    explicit = (vendor.get("platform") or "").strip().lower()
    if explicit in ("rtb56", "common_pack", "topda", "nextsls", "huawell_cms", "txfba"):
        return explicit
    if vendor.get("appToken") and vendor.get("appKey"):
        return "rtb56"
    api_url_lower = (vendor.get("apiUrl") or "").lower()
    if "/cms/tracking" in api_url_lower:
        return "huawell_cms"
    if vendor.get("FACTNO") and vendor.get("apiUrl"):
        return "common_pack"
    host = (vendor.get("host") or "").strip()
    api_url = (vendor.get("apiUrl") or "").strip()
    if host and api_url and "pubtracking" in api_url.lower():
        return "topda"
    if "nextsls.com" in api_url_lower:
        return "nextsls"
    if "txfba.com" in api_url_lower:
        return "txfba"
    return None


def resolve_vendor_for_row(
    row: dict[str, str],
    vendor_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """承运商编码 / 供应商名 与 config vendor name（及 aliases）匹配。"""
    candidates = [
        (row.get("carrier_code") or "").strip(),
        (row.get("supplier_name") or "").strip(),
    ]
    for name in candidates:
        if not name:
            continue
        if name in vendor_map:
            return vendor_map[name]
        for vendor in vendor_map.values():
            aliases = [vendor.get("name") or "", *(vendor.get("aliases") or [])]
            if name in {a.strip() for a in aliases if a and str(a).strip()}:
                return vendor
    return None


def _normalize_details(raw_details: list[dict[str, Any]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for item in raw_details:
        t = normalize_tracking_time(item.get("track_occur_date") or item.get("zztm") or "")
        d = (item.get("track_description") or item.get("guiji") or "").strip()
        if t:
            out.append((t, d))
    return out


def _topda_event_time(raw: str) -> str:
    return normalize_tracking_time(raw)


def _sort_logs_desc(logs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for item in logs:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return sorted(unique, key=lambda x: x[0], reverse=True)


def parse_topda_item(item: dict[str, Any]) -> list[tuple[str, str]]:
    """解析拓普达 pubTracking 单条结果 → [(time, desc), ...] 按时间倒序。"""
    logs: list[tuple[str, str]] = []
    for tr in item.get("trackings") or []:
        if not isinstance(tr, dict):
            continue
        t = _topda_event_time(tr.get("time") or tr.get("eventTime") or "")
        d = (tr.get("context") or "").strip()
        if t and d:
            logs.append((t, d))
    for hn in item.get("headNodes") or []:
        if not isinstance(hn, dict):
            continue
        t = _topda_event_time(hn.get("time") or hn.get("eventTime") or "")
        node = (hn.get("node") or "").strip()
        d = (hn.get("context") or "").strip() or _TOPDA_NODE_LABELS.get(node, node)
        if t and d:
            logs.append((t, d))
    return _sort_logs_desc(logs)


def _nextsls_mode(vendor: dict[str, Any]) -> str:
    """lists：/rest/trace/tracking/lists + app；app：/tracking/app + tracking_number。"""
    explicit = (vendor.get("nextslsMode") or vendor.get("nextsls_mode") or "").strip().lower()
    if explicit in ("app", "lists"):
        return explicit
    api_url = (vendor.get("apiUrl") or "").lower()
    if "/tracking/app" in api_url:
        return "app"
    return "lists"


def _nextsls_number_param(vendor: dict[str, Any]) -> str:
    explicit = (vendor.get("numberParam") or vendor.get("number_param") or "").strip()
    if explicit in ("number", "numbers"):
        return explicit
    api_url = (vendor.get("apiUrl") or "").lower()
    if "tracking/lists" in api_url:
        return "number"
    return "numbers"


def parse_nextsls_shipment(shipment: dict[str, Any]) -> list[tuple[str, str]]:
    """NextSLS（皓鹏 lists / 欧科 trace）单票 shipment → 轨迹列表，时间倒序。"""
    logs: list[tuple[str, str]] = []
    for tr in shipment.get("traces") or []:
        if not isinstance(tr, dict):
            continue
        t = _topda_event_time(tr.get("time") or "")
        d = (tr.get("info") or "").strip()
        if t and d:
            logs.append((t, d))
    return _sort_logs_desc(logs)


def _topda_item_keys(item: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for field in ("trackingNum", "poNum", "jobNum"):
        v = (item.get(field) or "").strip()
        if v:
            keys.append(v)
    return keys


def parse_txfba_track_list(items: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """腾信 getOrderTrackList → [(trackTime, trackInfo), ...] 时间倒序。"""
    logs: list[tuple[str, str]] = []
    for tr in items:
        if not isinstance(tr, dict):
            continue
        t = normalize_tracking_time(tr.get("trackTime") or "")
        d = (tr.get("trackInfo") or "").strip()
        if t and d:
            logs.append((t, d))
    return _sort_logs_desc(logs)


def fetch_tracking_batch(
    tracking_numbers: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, CarrierFetch]:
    """批量查询；返回 {运单号: (轨迹, 错误, carrier_id, tracking_number)}。"""
    cleaned = list(dict.fromkeys(n.strip() for n in tracking_numbers if n and n.strip()))
    if not cleaned:
        return {}
    platform = detect_platform(vendor)
    if platform == "topda":
        return _fetch_topda_batch(cleaned, vendor, timeout=timeout)
    if platform == "huawell_cms":
        return _fetch_huawell_cms_batch(cleaned, vendor, timeout=timeout)
    out: dict[str, CarrierFetch] = {}
    for num in cleaned:
        out[num] = fetch_tracking_one(num, vendor, timeout=timeout)
    return out


def fetch_tracking_one(
    tracking_number: str,
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> CarrierFetch:
    """返回 (轨迹列表, 错误, carrier_id, tracking_number)。"""
    sn = tracking_number.strip()
    platform = detect_platform(vendor)
    if platform == "rtb56":
        return _fetch_rtb56(sn, vendor, timeout=timeout)
    if platform == "common_pack":
        return _fetch_common_pack(sn, vendor, timeout=timeout)
    if platform == "topda":
        return _fetch_topda_batch([sn], vendor, timeout=timeout).get(
            sn, ([], "未返回", None, None)
        )
    if platform == "nextsls":
        return _fetch_nextsls(sn, vendor, timeout=timeout)
    if platform == "huawell_cms":
        return _fetch_huawell_cms_batch([sn], vendor, timeout=timeout).get(
            sn, ([], "未返回", None, None)
        )
    if platform == "txfba":
        return _carrier_fail("腾信请使用运单 carrier_id（billNo）查询，不支持按运单号直查")
    return _carrier_fail(f"未知平台: {vendor.get('name')}")


def _fetch_rtb56(
    tracking_number: str,
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> CarrierFetch:
    params = {
        "appToken": vendor["appToken"],
        "appKey": vendor["appKey"],
        "serviceMethod": "gettrack",
        "paramsJson": json.dumps({"tracking_number": tracking_number}, ensure_ascii=False),
    }
    try:
        resp = requests.post(vendor["apiUrl"], data=params, timeout=timeout)
        resp.raise_for_status()
        result = resp.json()
    except Exception as exc:
        return _carrier_fail(str(exc))
    if not result.get("success"):
        return _carrier_fail(result.get("cnmessage") or "承运商 API 返回失败")
    data = result.get("data") or []
    if not data:
        return _carrier_ok([])
    first = data[0] if isinstance(data, list) else data
    details = first.get("details") or []
    return _carrier_ok(_normalize_details(details))


def _parse_nextsls_json(result: Any) -> CarrierFetch:
    if not isinstance(result, dict):
        return _carrier_fail("NextSLS 响应格式异常")
    if result.get("status") != 1:
        msg = (result.get("info") or result.get("message") or "").strip()
        return _carrier_fail(msg or "NextSLS 查询失败")
    data = result.get("data")
    if not isinstance(data, dict):
        return _carrier_ok([])
    shipment = data.get("shipment")
    if not isinstance(shipment, dict):
        return _carrier_ok([])
    return _carrier_ok(
        parse_nextsls_shipment(shipment),
        _extract_carrier_id(shipment),
        _extract_outer_tracking_number(shipment),
    )


def _fetch_nextsls(
    tracking_number: str,
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> CarrierFetch:
    api_url = (vendor.get("apiUrl") or "").strip()
    if not api_url:
        return _carrier_fail("NextSLS 配置缺少 apiUrl")
    mode = _nextsls_mode(vendor)
    headers = {"Accept": "application/json"}
    if mode == "app":
        params: dict[str, str] = {
            "inajax": "1",
            "tracking_number": tracking_number,
        }
    else:
        app = (vendor.get("app") or vendor.get("appKey") or "").strip()
        if not app:
            return _carrier_fail("NextSLS lists 接口配置缺少 app")
        if api_url.rstrip("/").endswith("/trace"):
            api_url = "https://tracking.nextsls.com/rest/trace/tracking/lists"
        number_param = _nextsls_number_param(vendor)
        if number_param == "numbers":
            number_param = "number"
        params = {"app": app, number_param: tracking_number}
    try:
        resp = requests.get(api_url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").lower()
        if "json" not in content_type and resp.text.lstrip().startswith("<"):
            return _carrier_fail("NextSLS 返回 HTML 而非 JSON，请检查 apiUrl 配置")
        result = resp.json()
    except json.JSONDecodeError:
        return _carrier_fail("NextSLS 响应非 JSON，请检查 apiUrl 与参数")
    except Exception as exc:
        return _carrier_fail(str(exc))
    return _parse_nextsls_json(result)


def _huawell_cms_packno(item: dict[str, Any]) -> str:
    return (item.get("packno") or item.get("supcode") or "").strip()


def _fetch_huawell_cms_batch(
    tracking_numbers: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> dict[str, CarrierFetch]:
    """华威尔 CMS 批量轨迹：POST order_numbers。"""
    api_url = (vendor.get("apiUrl") or "http://47.115.60.246:8000/cms/tracking").strip()
    uuid_val = (vendor.get("uuid") or vendor.get("UUID") or "").strip()
    body = {"order_numbers": tracking_numbers, "uuid": uuid_val}
    out: dict[str, CarrierFetch] = {n: ([], None, None, None) for n in tracking_numbers}
    try:
        resp = requests.post(api_url, json=body, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        err = str(exc)
        return {n: ([], err, None, None) for n in tracking_numbers}
    if not isinstance(payload, list):
        return {n: ([], "华威尔 CMS 响应格式异常", None, None) for n in tracking_numbers}
    for item in payload:
        if not isinstance(item, dict):
            continue
        logs = _sort_logs_desc(_normalize_details(item.get("details") or []))
        cid = _extract_carrier_id(item)
        tn = _extract_outer_tracking_number(item)
        keys: set[str] = set()
        pn = _huawell_cms_packno(item)
        if pn:
            keys.add(pn)
        for field in ("supcode", "packno"):
            v = (item.get(field) or "").strip()
            if v:
                keys.add(v)
        for key in keys:
            if key in out:
                out[key] = (logs, None, cid or None, tn or None)
    return out


def _fetch_common_pack(
    tracking_number: str,
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> CarrierFetch:
    params = {
        "FACTNO": vendor["FACTNO"],
        "SUPNO": vendor["SUPNO"],
        "SUPPASS": vendor["SUPPASS"],
        "APPKEY": vendor["APPKEY"],
        "PACKNO": [tracking_number],
    }
    try:
        resp = requests.post(vendor["apiUrl"], json=params, timeout=timeout)
        resp.raise_for_status()
        result = resp.json()
    except Exception as exc:
        return _carrier_fail(str(exc))
    data = result.get("data") if isinstance(result, dict) else None
    if not data or "details" not in data:
        msg = result.get("msg") if isinstance(result, dict) else "响应格式异常"
        return _carrier_fail(msg)
    return _carrier_ok(_normalize_details(data.get("details") or []))


def _txfba_request_headers(vendor: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    token = (vendor.get("token") or vendor.get("appToken") or "").strip()
    if token:
        header_name = (vendor.get("tokenHeader") or "token").strip() or "token"
        headers[header_name] = token
    extra = vendor.get("headers")
    if isinstance(extra, dict):
        headers.update({str(k): str(v) for k, v in extra.items()})
    cookie = (vendor.get("cookie") or "").strip()
    if cookie:
        headers["Cookie"] = cookie
    return headers


def _fetch_txfba_track_by_bill_no(
    bill_no: str,
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> CarrierFetch:
    """腾信 getOrderTrackList：按 billNo（运单 carrier_id）拉全量轨迹。"""
    api_url = (
        vendor.get("apiUrl")
        or "https://interface.txfba.com/bussOrderTrack/getOrderTrackList"
    ).strip()
    body = {"billNo": bill_no.strip()}
    try:
        resp = requests.post(
            api_url,
            json=body,
            headers=_txfba_request_headers(vendor),
            timeout=timeout,
        )
        try:
            payload = resp.json()
        except Exception:
            payload = None
        if resp.status_code >= 400:
            snippet = (resp.text or "")[:200].replace("\n", " ")
            return _carrier_fail(
                f"HTTP {resp.status_code} {snippet or resp.reason}"
            )
        if payload is None:
            return _carrier_fail("腾信响应非 JSON")
    except Exception as exc:
        return _carrier_fail(str(exc))

    if not isinstance(payload, dict):
        return _carrier_fail("腾信 API 响应格式异常")
    if payload.get("code") != 200:
        msg = (payload.get("message") or "").strip() or "腾信查询失败"
        return _carrier_fail(f"code={payload.get('code')} {msg}")

    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return _carrier_ok([])

    logs = parse_txfba_track_list(data)
    tn = ""
    for item in data:
        if isinstance(item, dict):
            tn = _extract_outer_tracking_number(item)
            if tn:
                break
    return _carrier_ok(logs, None, tn or None)


def fetch_txfba_batch_for_rows(
    rows: list[dict[str, str]],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, CarrierFetch]:
    """按运单行查询：carrier_id 为腾信 billNo，结果键为 shipment_no。"""
    out: dict[str, CarrierFetch] = {}
    for row in rows:
        sn = row["shipment_no"]
        bill_no = (row.get("carrier_id") or "").strip()
        if not bill_no:
            out[sn] = ([], "腾信查询缺少 carrier_id（billNo，请手动填写）", None, None)
            continue
        logs, err, _, tn = _fetch_txfba_track_by_bill_no(bill_no, vendor, timeout=timeout)
        if err:
            out[sn] = ([], err, None, None)
            continue
        out[sn] = (logs, None, None, tn)
    return out


def _fetch_topda_batch(
    tracking_numbers: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> dict[str, CarrierFetch]:
    host = (vendor.get("host") or "topda.ai-ops.vip").strip()
    api_url = (vendor.get("apiUrl") or f"https://{host}/edi/pubTracking").strip()
    public_url = (vendor.get("publicUrl") or vendor.get("url") or "/public-tracking").strip()
    no_sub = vendor.get("noSubTracking", True)

    # 多单号用空格分隔；勿用 '+' 字面量（requests 会编码为 %2B 导致整串当一个单号）
    so_num = " ".join(tracking_numbers)
    query = urlencode(
        {
            "host": host,
            "noSubTracking": "true" if no_sub else "false",
            "soNum": so_num,
            "url": public_url,
        },
        safe="",
    )
    url = f"{api_url}?{query}"
    out: dict[str, CarrierFetch] = {n: ([], None, None, None) for n in tracking_numbers}
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        err = str(exc)
        return {n: ([], err, None, None) for n in tracking_numbers}

    if not isinstance(payload, list):
        err = "拓普达 API 响应格式异常"
        return {n: ([], err, None, None) for n in tracking_numbers}

    for item in payload:
        if not isinstance(item, dict):
            continue
        logs = parse_topda_item(item)
        if item.get("notFound"):
            logs = []
        cid = _extract_carrier_id(item)
        tn = _extract_outer_tracking_number(item)
        keys = _topda_item_keys(item)
        if not keys:
            continue
        for key in keys:
            if key in out:
                out[key] = (logs, None, cid or None, tn or None)
    return out


def latest_from_logs(logs: list[tuple[str, str]]) -> tuple[str, str]:
    if not logs:
        return "", ""
    return logs[0][0], logs[0][1]
