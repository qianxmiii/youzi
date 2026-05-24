"""承运商大类 API：从 config.json vendors 拉取轨迹。"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import requests

from ..carrier_tracking_entry import (
    CarrierTrackingLogEntry,
    coerce_carrier_logs,
    latest_from_logs,
    sort_logs_desc,
)
from ..db.datetime_util import normalize_tracking_time
from ..last_mile_tracking import normalize_tracking_field_value
from .sync_log_format import format_api_payload_for_log

BATCH_SIZE = 10
DEFAULT_TIMEOUT = 30

LogFn = Callable[[str], None]

# (轨迹列表, 错误, carrier_id, 主单号/尾程 tracking_number, 全部追踪号含主单)
CarrierFetch = tuple[
    list[CarrierTrackingLogEntry],
    str | None,
    str | None,
    str | None,
    list[str] | None,
]


def _vendor_ssl_verify(vendor: dict[str, Any], *, default: bool = True) -> bool:
    """config 中 sslVerify: false 时跳过证书校验（WY等站点证书/代理常不匹配）。"""
    raw = vendor.get("sslVerify")
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def _carrier_ok(
    logs: list[CarrierTrackingLogEntry] | list,
    carrier_id: str | None = None,
    tracking_number: str | None = None,
    tracking_numbers: list[str] | None = None,
) -> CarrierFetch:
    cid = (carrier_id or "").strip() or None
    tn = normalize_tracking_field_value(tracking_number) if tracking_number else None
    entries = sort_logs_desc(coerce_carrier_logs(logs))
    extra = None
    if tracking_numbers:
        extra = [
            normalize_tracking_field_value(n) or (n or "").strip()
            for n in tracking_numbers
            if (n or "").strip()
        ]
        extra = list(dict.fromkeys(extra))
    return entries, None, cid, tn, extra or None


def _carrier_fail(msg: str) -> CarrierFetch:
    return [], msg, None, None, None


def unpack_carrier_fetch(raw: CarrierFetch | tuple[Any, ...]) -> CarrierFetch:
    """兼容 4 元组旧返回值。"""
    if len(raw) >= 5:
        return (
            raw[0],
            raw[1],
            raw[2],
            raw[3],
            raw[4] if len(raw) > 4 else None,
        )
    return raw[0], raw[1], raw[2], raw[3], None


def parse_topda_tracking_bundle(
    item: dict[str, Any],
) -> tuple[str | None, str | None, list[str]]:
    """
    TOPDA pubTracking：jobNum、subTrackings 下 trackingNum。
    第一个子单 trackingNum 为主单号（写入 shipments.tracking_number），
    全部子单号入库（主单号 is_main=1，且本身也在子单列表中）。
    """
    job = (item.get("jobNum") or "").strip() or None
    numbers: list[str] = []
    seen: set[str] = set()

    for st in item.get("subTrackings") or []:
        if not isinstance(st, dict):
            continue
        n = normalize_tracking_field_value(st.get("trackingNum"))
        if n and n not in seen:
            seen.add(n)
            numbers.append(n)

    main = numbers[0] if numbers else None
    return job, main, numbers


def _repair_utf8_mojibake(text: str) -> str:
    """修复 UTF-8 被误按 Latin-1 解码后再存回的乱码（如壹合 NextSLS text/html 响应）。"""
    if not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def _maybe_repair_text(text: str) -> str:
    s = (text or "").strip()
    if not s or all(ord(c) < 128 for c in s):
        return s
    repaired = _repair_utf8_mojibake(s)
    return repaired if repaired != s else s


def _response_json(resp: requests.Response) -> Any:
    """按 UTF-8 解析 JSON，避免 Content-Type 为 text/html 时 requests 误用 Latin-1。"""
    try:
        return json.loads(resp.content.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(resp.content.decode("utf-8", errors="replace"))


def _extract_carrier_id(data: dict[str, Any]) -> str:
    """NextSLS shipment_id、Topda jobNum、HWE orderno 等。"""
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
        v = normalize_tracking_field_value(data.get(key))
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
    if explicit in (
        "rtb56",
        "common_pack",
        "topda",
        "nextsls",
        "huawell_cms",
        "txfba",
        "wy",
        "yorky",
        "juren",
        "qiyun",
        "olt",
        "haojie",
    ):
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
    if "wy-express.com" in api_url_lower:
        return "wy"
    if "56yorky.com" in api_url_lower:
        return "yorky"
    if "tracequery/out/list" in api_url_lower or "tms-saas" in api_url_lower:
        return "juren"
    if "webtrack" in api_url_lower:
        return "qiyun"
    if "120.24.174.13" in api_url_lower:
        return "haojie"
    if "olt56.com" in api_url_lower:
        return "olt"
    if "/tracklist" in api_url_lower:
        return "olt"
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


def carrier_vendor_unassigned_reason(
    row: dict[str, str],
    vendor_map: dict[str, dict[str, Any]],
) -> str:
    """说明运单为何未匹配到 config.json 中的 vendors。"""
    cc = (row.get("carrier_code") or "").strip()
    sup = (row.get("supplier_name") or "").strip()
    if not cc and not sup:
        sample = "、".join(sorted(vendor_map.keys())[:6])
        return f"未填写承运商/供应商，请在运单中填写以匹配 config：{sample}…"
    label = cc or sup
    return f"承运商/供应商「{label}」与 config.vendors 未匹配，请改运单或补 aliases"


def _normalize_details(raw_details: list[dict[str, Any]]) -> list[CarrierTrackingLogEntry]:
    out: list[CarrierTrackingLogEntry] = []
    for item in raw_details:
        t = normalize_tracking_time(item.get("track_occur_date") or item.get("zztm") or "")
        d = _maybe_repair_text(item.get("track_description") or item.get("guiji") or "")
        if t:
            out.append(CarrierTrackingLogEntry.from_row(t, d))
    return out


def _topda_event_time(raw: str) -> str:
    return normalize_tracking_time(raw)


def _topda_row_time(row: dict[str, Any]) -> str:
    """Topda：eventTime 含秒，优先于 time（仅到分钟）。"""
    return _topda_event_time(row.get("eventTime") or row.get("time") or "")


def _topda_tracking_event_id(tr: dict[str, Any]) -> str | None:
    raw = tr.get("id")
    if raw is None:
        return None
    s = str(raw).strip()
    return f"topda:{s}" if s else None


def _topda_head_event_id(hn: dict[str, Any]) -> str | None:
    node = (hn.get("node") or "").strip()
    if not node:
        return None
    gid = hn.get("guideId")
    if gid is not None and str(gid).strip():
        return f"topda-head:{gid}:{node}"
    t = _topda_row_time(hn)
    if t:
        return f"topda-head:{node}:{t}"
    return f"topda-head:{node}"


def parse_topda_item(item: dict[str, Any]) -> list[CarrierTrackingLogEntry]:
    """解析Topda pubTracking 单条结果 → 轨迹列表（含 trackings.id）按时间倒序。"""
    logs: list[CarrierTrackingLogEntry] = []
    tracking_nodes: set[str] = set()
    for tr in item.get("trackings") or []:
        if not isinstance(tr, dict):
            continue
        node = (tr.get("node") or "").strip()
        if node:
            tracking_nodes.add(node)
        t = _topda_row_time(tr)
        d = _maybe_repair_text(tr.get("context") or "")
        if t and d:
            logs.append(
                CarrierTrackingLogEntry.from_row(t, d, _topda_tracking_event_id(tr))
            )
    for hn in item.get("headNodes") or []:
        if not isinstance(hn, dict):
            continue
        node = (hn.get("node") or "").strip()
        if node and node in tracking_nodes:
            continue
        t = _topda_row_time(hn)
        d = _maybe_repair_text(hn.get("context") or "") or _TOPDA_NODE_LABELS.get(node, node)
        if t and d:
            logs.append(
                CarrierTrackingLogEntry.from_row(t, d, _topda_head_event_id(hn))
            )
    return sort_logs_desc(logs)


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


def parse_nextsls_shipment(shipment: dict[str, Any]) -> list[CarrierTrackingLogEntry]:
    """NextSLS（皓鹏 lists / 欧科 trace）单票 shipment → 轨迹列表，时间倒序。"""
    logs: list[CarrierTrackingLogEntry] = []
    for tr in shipment.get("traces") or []:
        if not isinstance(tr, dict):
            continue
        t = _topda_event_time(tr.get("time") or "")
        d = _maybe_repair_text(tr.get("info") or "")
        if t and d:
            logs.append(CarrierTrackingLogEntry.from_row(t, d))
    return sort_logs_desc(logs)


def _topda_item_keys(item: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for field in ("trackingNum", "poNum", "jobNum"):
        v = (item.get(field) or "").strip()
        if v:
            keys.append(v)
    return keys


def _txfba_detail_api_url(vendor: dict[str, Any]) -> str:
    return (
        vendor.get("detailApiUrl")
        or vendor.get("apiUrl")
        or "https://interface.txfba.com/bussOrderTrack/getOrderTrackDetailList"
    ).strip()


def _txfba_request_headers(vendor: dict[str, Any]) -> dict[str, str]:
    # TX网关要求 ownersystem（与 txfba.com 员工端一致）；缺省会返回 HTTP 404 而非 CORS 问题
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "ownersystem": (vendor.get("ownersystem") or "EMPLOYEE_TERMINAL").strip()
        or "EMPLOYEE_TERMINAL",
    }
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


def _txfba_track_desc(tr: dict[str, Any]) -> str:
    name = _maybe_repair_text((tr.get("trackName") or "").strip())
    info = _maybe_repair_text((tr.get("trackInfo") or "").strip())
    if name and info and name not in info:
        return f"{name}：{info}"
    return info or name


def _txfba_event_id(tr: dict[str, Any]) -> str | None:
    raw = tr.get("billTrackNo")
    if raw is None:
        return None
    s = str(raw).strip()
    return f"txfba:{s}" if s else None


def parse_txfba_detail_group(item: dict[str, Any]) -> tuple[list[CarrierTrackingLogEntry], str | None, str | None]:
    """TX getOrderTrackDetailList 单条 data：billNo=carrier_id，trackTime/trackInfo=轨迹。"""
    carrier_id = (str(item.get("billNo") or "")).strip() or None
    express_main: str | None = None
    logs: list[CarrierTrackingLogEntry] = []
    for tr in item.get("trackList") or []:
        if not isinstance(tr, dict):
            continue
        t = normalize_tracking_time(tr.get("trackTime") or "")
        d = _txfba_track_desc(tr)
        if not t or not d:
            continue
        if not express_main:
            em = (str(tr.get("expressMainNo") or "")).strip()
            if em:
                express_main = em
        logs.append(CarrierTrackingLogEntry.from_row(t, d, _txfba_event_id(tr)))
    return sort_logs_desc(logs), carrier_id, express_main


def _txfba_format_http_error(resp: requests.Response) -> str:
    try:
        payload = _response_json(resp)
        if isinstance(payload, dict):
            msg = _maybe_repair_text(
                str(payload.get("message") or payload.get("error") or "")
            )
            if msg:
                return f"HTTP {resp.status_code}: {msg}"
    except Exception:
        pass
    hint = ""
    if resp.status_code in (401, 403, 404):
        hint = "（请检查 config 中TX token/cookie 是否已配置）"
    return f"HTTP {resp.status_code}{hint}"


def _txfba_post_detail(
    bill_no_list: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> tuple[list[dict[str, Any]], str | None]:
    api_url = _txfba_detail_api_url(vendor)
    body = {"billNoList": bill_no_list}
    try:
        resp = requests.post(
            api_url,
            json=body,
            headers=_txfba_request_headers(vendor),
            timeout=timeout,
        )
        if resp.status_code >= 400:
            return [], _txfba_format_http_error(resp)
        payload = _response_json(resp)
    except requests.RequestException as exc:
        return [], str(exc)
    if not isinstance(payload, dict):
        return [], "TX API 响应格式异常"
    code = payload.get("code")
    if code not in (200, "200"):
        msg = _maybe_repair_text(str(payload.get("message") or payload.get("msg") or ""))
        return [], msg or f"code={code}"
    data = payload.get("data")
    if not isinstance(data, list):
        return [], None
    return [x for x in data if isinstance(x, dict)], None


def _txfba_bill_for_row(row: dict[str, str], vendor: dict[str, Any] | None = None) -> str:
    """billNoList 查询键：默认运单号（customerBillNo）；可配置 txfbaBillNoMode=carrier_id。"""
    sn = (row.get("shipment_no") or "").strip()
    cid = (row.get("carrier_id") or "").strip()
    mode = ((vendor or {}).get("txfbaBillNoMode") or "").strip().lower()
    if mode == "carrier_id":
        return cid or sn
    return sn or cid


def _txfba_target_shipments(
    item: dict[str, Any],
    bill_to_sns: dict[str, set[str]],
    pending_sns: set[str],
) -> set[str]:
    targets: set[str] = set()
    group_bill = (str(item.get("billNo") or "")).strip()
    if group_bill:
        targets.update(bill_to_sns.get(group_bill, set()))
    for tr in item.get("trackList") or []:
        if not isinstance(tr, dict):
            continue
        cbn = (str(tr.get("customerBillNo") or "")).strip()
        if cbn and cbn in pending_sns:
            targets.add(cbn)
    return targets


def fetch_txfba_batch_for_rows(
    rows: list[dict[str, str]],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    """TX批量：POST billNoList（默认运单号；响应 billNo 回写 carrier_id）。"""
    out: dict[str, CarrierFetch] = {}
    bill_to_sns: dict[str, set[str]] = {}
    for row in rows:
        sn = (row.get("shipment_no") or "").strip()
        if not sn:
            continue
        out[sn] = ([], None, None, None, None)
        bill = _txfba_bill_for_row(row, vendor)
        if not bill:
            out[sn] = ([], "TX查询缺少 billNo（需运单号）", None, None)
            continue
        bill_to_sns.setdefault(bill, set()).add(sn)

    bills = [b for b in bill_to_sns if b]
    if not bills:
        return out

    pending = set(out.keys())
    for i in range(0, len(bills), BATCH_SIZE):
        chunk = bills[i : i + BATCH_SIZE]
        groups, err = _txfba_post_detail(chunk, vendor, timeout=timeout)
        if err:
            for bill in chunk:
                for sn in bill_to_sns.get(bill, set()):
                    out[sn] = ([], err, None, None)
            continue
        matched: set[str] = set()
        for item in groups:
            targets = _txfba_target_shipments(item, bill_to_sns, pending)
            if not targets:
                continue
            logs, cid, tn = parse_txfba_detail_group(item)
            for sn in targets:
                out[sn] = (logs, None, cid, tn)
                matched.add(sn)
                if log is not None:
                    log(
                        f"[承运商轨迹] {sn} 返回报文 {format_api_payload_for_log(item)}"
                    )
        for bill in chunk:
            for sn in bill_to_sns.get(bill, set()):
                if sn not in matched and out[sn][1] is None:
                    out[sn] = ([], "TX API 未返回该单", None, None)
    return out


def _wy_api_url(vendor: dict[str, Any]) -> str:
    return (
        vendor.get("detailApiUrl")
        or vendor.get("apiUrl")
        or "https://www.wy-express.com/root-api/c/order/getPublicLogisticsTrackList"
    ).strip()


def _wy_request_headers(vendor: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    auth = (
        (vendor.get("authorization") or vendor.get("Authorization") or "")
    ).strip()
    if auth:
        headers["authorization"] = auth
    token = (vendor.get("token") or vendor.get("appToken") or "").strip()
    if token:
        header_name = (vendor.get("tokenHeader") or "authorization").strip() or "authorization"
        headers[header_name] = token
    extra = vendor.get("headers")
    if isinstance(extra, dict):
        headers.update({str(k): str(v) for k, v in extra.items()})
    return headers


def _wy_track_desc(node: dict[str, Any]) -> str:
    name = _maybe_repair_text((node.get("nodeName") or "").strip())
    info = _maybe_repair_text((node.get("nodeDesc") or "").strip())
    if name and info and name not in info:
        return f"{name}：{info}"
    return info or name


def _wy_event_id(node: dict[str, Any]) -> str | None:
    raw = node.get("id")
    if raw is None:
        return None
    s = str(raw).strip()
    return f"wy:{s}" if s else None


def parse_wy_track_group(item: dict[str, Any]) -> tuple[list[CarrierTrackingLogEntry], str | None, str | None]:
    """WY单条 trackList：customerOrderNumber=查询键，systemOrderNumber=carrier_id。"""
    carrier_id = (str(item.get("systemOrderNumber") or "")).strip() or None
    logs: list[CarrierTrackingLogEntry] = []
    for group in item.get("list") or []:
        if not isinstance(group, dict):
            continue
        for node in group.get("childNodeList") or []:
            if not isinstance(node, dict):
                continue
            t = normalize_tracking_time(node.get("nodeTime") or "")
            d = _wy_track_desc(node)
            if not t or not d:
                continue
            logs.append(CarrierTrackingLogEntry.from_row(t, d, _wy_event_id(node)))
    return sort_logs_desc(logs), carrier_id, None


def _wy_format_http_error(resp: requests.Response) -> str:
    try:
        payload = _response_json(resp)
        if isinstance(payload, dict):
            msg = _maybe_repair_text(str(payload.get("msg") or payload.get("message") or ""))
            if msg:
                return f"HTTP {resp.status_code}: {msg}"
    except Exception:
        pass
    hint = ""
    if resp.status_code in (401, 403):
        hint = "（请检查 config 中WY authorization 是否已配置）"
    return f"HTTP {resp.status_code}{hint}"


def _wy_post_track(
    order_no_list: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> tuple[list[dict[str, Any]], str | None]:
    api_url = _wy_api_url(vendor)
    body = {"customerOrderNumberList": order_no_list}
    headers = _wy_request_headers(vendor)
    if not headers.get("authorization"):
        return [], "WY缺少 authorization 配置"
    verify_ssl = _vendor_ssl_verify(vendor, default=False)
    try:
        resp = requests.post(
            api_url,
            json=body,
            headers=headers,
            timeout=timeout,
            verify=verify_ssl,
        )
        if resp.status_code >= 400:
            return [], _wy_format_http_error(resp)
        payload = _response_json(resp)
    except requests.RequestException as exc:
        msg = str(exc)
        if verify_ssl and ("CERTIFICATE_VERIFY_FAILED" in msg or "SSLError" in msg):
            msg += "（可在 config WY项设置 \"sslVerify\": false）"
        return [], msg
    if not isinstance(payload, dict):
        return [], "WY API 响应格式异常"
    code = payload.get("code")
    if code not in (200, "200"):
        msg = _maybe_repair_text(str(payload.get("msg") or payload.get("message") or ""))
        return [], msg or f"code={code}"
    data = payload.get("data")
    if isinstance(data, dict):
        track_list = data.get("trackList")
        if isinstance(track_list, list):
            return [x for x in track_list if isinstance(x, dict)], None
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)], None
    return [], None


def _wy_order_no_for_row(row: dict[str, str], vendor: dict[str, Any] | None = None) -> str:
    sn = (row.get("shipment_no") or "").strip()
    cid = (row.get("carrier_id") or "").strip()
    mode = ((vendor or {}).get("wyOrderNoMode") or "").strip().lower()
    if mode in ("system_order", "carrier_id"):
        return cid or sn
    return sn or cid


def _wy_target_shipments(
    item: dict[str, Any],
    order_to_sns: dict[str, set[str]],
    pending_sns: set[str],
) -> set[str]:
    targets: set[str] = set()
    for key in ("customerOrderNumber", "systemOrderNumber"):
        val = (str(item.get(key) or "")).strip()
        if val:
            targets.update(order_to_sns.get(val, set()))
    cust = (str(item.get("customerOrderNumber") or "")).strip()
    if cust and cust in pending_sns:
        targets.add(cust)
    return targets


def fetch_wy_batch_for_rows(
    rows: list[dict[str, str]],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    """WY批量：POST customerOrderNumberList（默认运单号）。"""
    out: dict[str, CarrierFetch] = {}
    order_to_sns: dict[str, set[str]] = {}
    for row in rows:
        sn = (row.get("shipment_no") or "").strip()
        if not sn:
            continue
        out[sn] = ([], None, None, None, None)
        order_no = _wy_order_no_for_row(row, vendor)
        if not order_no:
            out[sn] = ([], "WY查询缺少 customerOrderNumber（需运单号）", None, None)
            continue
        order_to_sns.setdefault(order_no, set()).add(sn)

    orders = [o for o in order_to_sns if o]
    if not orders:
        return out

    pending = set(out.keys())
    for i in range(0, len(orders), BATCH_SIZE):
        chunk = orders[i : i + BATCH_SIZE]
        groups, err = _wy_post_track(chunk, vendor, timeout=timeout)
        if err:
            for order_no in chunk:
                for sn in order_to_sns.get(order_no, set()):
                    out[sn] = ([], err, None, None)
            continue
        matched: set[str] = set()
        for item in groups:
            targets = _wy_target_shipments(item, order_to_sns, pending)
            if not targets:
                continue
            logs, cid, tn = parse_wy_track_group(item)
            for sn in targets:
                out[sn] = (logs, None, cid, tn)
                matched.add(sn)
                if log is not None:
                    log(
                        f"[承运商轨迹] {sn} 返回报文 {format_api_payload_for_log(item)}"
                    )
        for order_no in chunk:
            for sn in order_to_sns.get(order_no, set()):
                if sn not in matched and out[sn][1] is None:
                    out[sn] = ([], "WY API 未返回该单", None, None)
    return out


def _yorky_api_url(vendor: dict[str, Any]) -> str:
    return (
        vendor.get("detailApiUrl")
        or vendor.get("apiUrl")
        or "https://www.56yorky.com/api/open/depot/trackInfo"
    ).strip()


def _yorky_request_headers(vendor: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    token = (
        (vendor.get("token") or vendor.get("appToken") or vendor.get("authorization") or "")
    ).strip()
    if token:
        header_name = (vendor.get("tokenHeader") or "Authorization").strip() or "Authorization"
        headers[header_name] = token
    extra = vendor.get("headers")
    if isinstance(extra, dict):
        headers.update({str(k): str(v) for k, v in extra.items()})
    return headers


def _yorky_query_params(vendor: dict[str, Any], track_nos: list[str]) -> dict[str, str]:
    return {
        "trackNos": ",".join(track_nos),
        "remove": str(vendor.get("remove") if vendor.get("remove") is not None else "T"),
        "language": str(vendor.get("language") or "zh_CN"),
    }


def _yorky_track_desc(node: dict[str, Any]) -> str:
    status = _maybe_repair_text((node.get("trackStatusText") or "").strip())
    info = _maybe_repair_text((node.get("trackDesc") or "").strip())
    if status and info and status not in info:
        return f"{status}：{info}"
    return info or status


def _yorky_event_id(raw: Any, *, prefix: str) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    return f"yorky:{prefix}:{s}" if s else None


def _yorky_logs_from_item(item: dict[str, Any]) -> list[CarrierTrackingLogEntry]:
    logs: list[CarrierTrackingLogEntry] = []
    for tr in item.get("trackInfoList") or []:
        if not isinstance(tr, dict):
            continue
        t = normalize_tracking_time(tr.get("trackTime") or "")
        d = _yorky_track_desc(tr)
        if not t or not d:
            continue
        logs.append(CarrierTrackingLogEntry.from_row(t, d, _yorky_event_id(tr.get("id"), prefix="t")))
    if not logs:
        for ch in item.get("inputChanges") or []:
            if not isinstance(ch, dict):
                continue
            t = normalize_tracking_time(ch.get("createTime") or "")
            code = _maybe_repair_text((ch.get("busiCode") or "").strip())
            remark = _maybe_repair_text((ch.get("remark") or "").strip())
            if code and remark and code not in remark:
                d = f"{code}：{remark}"
            else:
                d = remark or code
            if not t or not d:
                continue
            logs.append(
                CarrierTrackingLogEntry.from_row(
                    t, d, _yorky_event_id(ch.get("changeSn"), prefix="c")
                )
            )
    return sort_logs_desc(logs)


def parse_yorky_track_item(item: dict[str, Any]) -> tuple[list[CarrierTrackingLogEntry], str | None, str | None]:
    """聚美：userNo=运单号，trackNo=尾程单号 tracking_number。"""
    logs = _yorky_logs_from_item(item)
    tn = (str(item.get("trackNo") or "")).strip() or None
    return logs, None, tn


def _yorky_get_track(
    track_nos: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> tuple[list[dict[str, Any]], str | None]:
    api_url = _yorky_api_url(vendor)
    try:
        resp = requests.get(
            api_url,
            params=_yorky_query_params(vendor, track_nos),
            headers=_yorky_request_headers(vendor),
            timeout=timeout,
            verify=_vendor_ssl_verify(vendor, default=True),
        )
        if resp.status_code >= 400:
            try:
                payload = _response_json(resp)
                msg = ""
                if isinstance(payload, dict):
                    msg = _maybe_repair_text(
                        str(payload.get("message") or payload.get("msg") or "")
                    )
                return [], f"HTTP {resp.status_code}" + (f": {msg}" if msg else "")
            except Exception:
                return [], f"HTTP {resp.status_code}"
        payload = _response_json(resp)
    except requests.RequestException as exc:
        return [], str(exc)
    if not isinstance(payload, dict):
        return [], "聚美 API 响应格式异常"
    code = payload.get("code")
    if code not in (200, "200"):
        msg = _maybe_repair_text(str(payload.get("message") or payload.get("msg") or ""))
        return [], msg or f"code={code}"
    data = payload.get("data")
    if not isinstance(data, list):
        return [], None
    return [x for x in data if isinstance(x, dict)], None


def _yorky_track_no_for_row(row: dict[str, str]) -> str:
    return (row.get("shipment_no") or "").strip()


def fetch_yorky_batch_for_rows(
    rows: list[dict[str, str]],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    """聚美批量：GET trackNos=运单号逗号分隔。"""
    out: dict[str, CarrierFetch] = {}
    sn_to_row: dict[str, str] = {}
    for row in rows:
        sn = (row.get("shipment_no") or "").strip()
        if not sn:
            continue
        out[sn] = ([], None, None, None, None)
        bill = _yorky_track_no_for_row(row)
        if not bill:
            out[sn] = ([], "聚美查询缺少运单号", None, None)
            continue
        sn_to_row[bill] = sn

    bills = list(sn_to_row.keys())
    if not bills:
        return out

    for i in range(0, len(bills), BATCH_SIZE):
        chunk = bills[i : i + BATCH_SIZE]
        groups, err = _yorky_get_track(chunk, vendor, timeout=timeout)
        if err:
            for bill in chunk:
                sn = sn_to_row[bill]
                out[sn] = ([], err, None, None)
            continue
        matched: set[str] = set()
        for item in groups:
            user_no = (str(item.get("userNo") or "")).strip()
            sn = sn_to_row.get(user_no)
            if not sn:
                continue
            logs, cid, tn = parse_yorky_track_item(item)
            out[sn] = (logs, None, cid, tn)
            matched.add(sn)
            if log is not None:
                log(f"[承运商轨迹] {sn} 返回报文 {format_api_payload_for_log(item)}")
        for bill in chunk:
            sn = sn_to_row[bill]
            if sn not in matched and out[sn][1] is None:
                out[sn] = ([], "聚美 API 未返回该单", None, None)
    return out


def _juren_api_url(vendor: dict[str, Any]) -> str:
    return (
        vendor.get("detailApiUrl")
        or vendor.get("apiUrl")
        or "http://39.108.124.3:21000/tms-saas-all/oms/tms/tracequery/out/list"
    ).strip()


def _juren_request_headers(vendor: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    token = (
        (vendor.get("token") or vendor.get("appToken") or vendor.get("authorization") or "")
    ).strip()
    if token:
        header_name = (vendor.get("tokenHeader") or "Authorization").strip() or "Authorization"
        headers[header_name] = token
    extra = vendor.get("headers")
    if isinstance(extra, dict):
        headers.update({str(k): str(v) for k, v in extra.items()})
    return headers


def _juren_query_params(vendor: dict[str, Any], shipment_nos: list[str]) -> dict[str, str]:
    sep = str(vendor.get("noListSeparator") or "\n")
    return {
        "noList": sep.join(shipment_nos),
        "queryType": str(vendor.get("queryType") if vendor.get("queryType") is not None else "99"),
        "companyId": str(vendor.get("companyId") if vendor.get("companyId") is not None else "32"),
    }


def _juren_track_time(node: dict[str, Any]) -> str:
    t = normalize_tracking_time(node.get("scanTime") or "")
    if t:
        return t
    raw_ms = node.get("scanDatetime")
    if isinstance(raw_ms, (int, float)) and raw_ms > 0:
        from datetime import datetime

        return datetime.fromtimestamp(float(raw_ms) / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
    return normalize_tracking_time(node.get("createDatetime") or "")


def _juren_track_desc(node: dict[str, Any]) -> str:
    status = _maybe_repair_text((node.get("scanStatus") or "").strip())
    remark = _maybe_repair_text((node.get("remark") or "").strip())
    if status and remark and status not in remark:
        return f"{status}：{remark}"
    return remark or status


def _juren_event_id(node: dict[str, Any]) -> str | None:
    ms = node.get("scanDatetime")
    code = (str(node.get("scanCode") or "")).strip()
    if isinstance(ms, (int, float)) and ms > 0:
        return f"juren:{int(ms)}:{code}" if code else f"juren:{int(ms)}"
    t = _juren_track_time(node)
    if t and code:
        return f"juren:{t}:{code}"
    if t:
        return f"juren:{t}"
    return None


def parse_juren_track_item(item: dict[str, Any]) -> tuple[list[CarrierTrackingLogEntry], str | None, str | None]:
    """JUREN：jobno=运单号，refno=尾程单号 tracking_number。"""
    logs: list[CarrierTrackingLogEntry] = []
    for node in item.get("podInfoDTOList") or []:
        if not isinstance(node, dict):
            continue
        if node.get("isshow") == 0:
            continue
        t = _juren_track_time(node)
        d = _juren_track_desc(node)
        if not t or not d:
            continue
        logs.append(CarrierTrackingLogEntry.from_row(t, d, _juren_event_id(node)))
    tn = (str(item.get("refno") or "")).strip() or None
    return sort_logs_desc(logs), None, tn


def _juren_get_track(
    shipment_nos: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> tuple[list[dict[str, Any]], str | None]:
    api_url = _juren_api_url(vendor)
    try:
        resp = requests.get(
            api_url,
            params=_juren_query_params(vendor, shipment_nos),
            headers=_juren_request_headers(vendor),
            timeout=timeout,
            verify=_vendor_ssl_verify(vendor, default=True),
        )
        if resp.status_code >= 400:
            try:
                payload = _response_json(resp)
                msg = ""
                if isinstance(payload, dict):
                    msg = _maybe_repair_text(
                        str(payload.get("message") or payload.get("solution") or "")
                    )
                return [], f"HTTP {resp.status_code}" + (f": {msg}" if msg else "")
            except Exception:
                return [], f"HTTP {resp.status_code}"
        payload = _response_json(resp)
    except requests.RequestException as exc:
        return [], str(exc)
    if not isinstance(payload, dict):
        return [], "JUREN API 响应格式异常"
    code = payload.get("result_code")
    if code not in (0, "0"):
        msg = _maybe_repair_text(str(payload.get("message") or payload.get("solution") or ""))
        return [], msg or f"result_code={code}"
    body = payload.get("body")
    if not isinstance(body, list):
        return [], None
    return [x for x in body if isinstance(x, dict)], None


def _juren_shipment_no_for_row(row: dict[str, str]) -> str:
    return (row.get("shipment_no") or "").strip()


def fetch_juren_batch_for_rows(
    rows: list[dict[str, str]],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    """JUREN 批量：GET noList=运单号（默认换行分隔）。"""
    out: dict[str, CarrierFetch] = {}
    sn_to_row: dict[str, str] = {}
    for row in rows:
        sn = (row.get("shipment_no") or "").strip()
        if not sn:
            continue
        out[sn] = ([], None, None, None, None)
        bill = _juren_shipment_no_for_row(row)
        if not bill:
            out[sn] = ([], "JUREN 查询缺少运单号", None, None)
            continue
        sn_to_row[bill] = sn

    bills = list(sn_to_row.keys())
    if not bills:
        return out

    for i in range(0, len(bills), BATCH_SIZE):
        chunk = bills[i : i + BATCH_SIZE]
        groups, err = _juren_get_track(chunk, vendor, timeout=timeout)
        if err:
            for bill in chunk:
                sn = sn_to_row[bill]
                out[sn] = ([], err, None, None)
            continue
        matched: set[str] = set()
        for item in groups:
            jobno = (str(item.get("jobno") or item.get("refno") or "")).strip()
            sn = sn_to_row.get(jobno)
            if not sn:
                continue
            logs, cid, tn = parse_juren_track_item(item)
            out[sn] = (logs, None, cid, tn)
            matched.add(sn)
            if log is not None:
                log(f"[承运商轨迹] {sn} 返回报文 {format_api_payload_for_log(item)}")
        for bill in chunk:
            sn = sn_to_row[bill]
            if sn not in matched and out[sn][1] is None:
                out[sn] = ([], "JUREN API 未返回该单", None, None)
    return out


def _qiyun_api_url(vendor: dict[str, Any]) -> str:
    return (
        vendor.get("detailApiUrl")
        or vendor.get("apiUrl")
        or "http://120.25.160.216:8080/WebTrack?action=repeat"
    ).strip()


def _qiyun_request_headers(vendor: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/xml, text/xml, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }
    extra = vendor.get("headers")
    if isinstance(extra, dict):
        headers.update({str(k): str(v) for k, v in extra.items()})
    cookie_raw = (
        vendor.get("cookie")
        or vendor.get("Cookie")
        or vendor.get("cookies")
        or vendor.get("Cookies")
        or ""
    )
    cookie = cookie_raw.strip() if isinstance(cookie_raw, str) else ""
    if cookie and "Cookie" not in headers:
        headers["Cookie"] = cookie
    return headers


def _qiyun_request_cookies(vendor: dict[str, Any]) -> dict[str, str] | None:
    raw = vendor.get("cookies")
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return None


def _qiyun_form_body(shipment_no: str, vendor: dict[str, Any]) -> dict[str, str]:
    bill_key = (vendor.get("billidParam") or "billid").strip() or "billid"
    return {
        "index": str(vendor.get("index") if vendor.get("index") is not None else "0"),
        bill_key: shipment_no,
        "isRepeat": str(vendor.get("isRepeat") if vendor.get("isRepeat") is not None else "no"),
        "language": str(vendor.get("language") or "zh"),
    }


def _qiyun_track_desc(place: str, intro: str) -> str:
    p = _maybe_repair_text(place)
    i = _maybe_repair_text(intro)
    if p and i and p not in i:
        return f"{p}：{i}"
    return i or p


def _qiyun_event_id(item: ET.Element) -> str | None:
    idx = (item.get("index") or "").strip()
    if idx:
        return f"qiyun:{idx}"
    t = normalize_tracking_time(item.get("sdate") or "")
    intro = (item.get("intro") or "").strip()
    if t and intro:
        return f"qiyun:{t}:{intro[:48]}"
    if t:
        return f"qiyun:{t}"
    return None


def _qiyun_find_track(root: ET.Element, expected_sn: str) -> ET.Element | None:
    tracks = root.findall(".//track")
    if not tracks:
        return None
    sn = expected_sn.strip()
    for tr in tracks:
        if (tr.get("refernum") or "").strip() == sn:
            return tr
    if len(tracks) == 1:
        return tracks[0]
    return None


def parse_qiyun_track_element(
    track: ET.Element,
    *,
    expected_sn: str = "",
) -> tuple[list[CarrierTrackingLogEntry], str | None, str | None]:
    """QIYUN：<track billid=carrier_id>，子节点 trackitem 为轨迹。"""
    refernum = (track.get("refernum") or "").strip()
    billid = (track.get("billid") or "").strip()
    sn = (expected_sn or refernum).strip()
    # 未登录时 billid 常回显运单号，不能当作 carrier_id
    cid = billid if billid and (not sn or billid != sn) else None
    tn = (track.get("transbillid") or track.get("newbillid") or "").strip() or None
    logs: list[CarrierTrackingLogEntry] = []
    for item in track.findall("trackitem"):
        t = normalize_tracking_time(item.get("sdate") or "")
        d = _qiyun_track_desc(item.get("place") or "", item.get("intro") or "")
        if not t or not d:
            continue
        logs.append(CarrierTrackingLogEntry.from_row(t, d, _qiyun_event_id(item)))
    return sort_logs_desc(logs), cid, tn


def _qiyun_empty_track_hint(track: ET.Element, expected_sn: str) -> str | None:
    if track.findall("trackitem"):
        return None
    refernum = (track.get("refernum") or "").strip()
    if refernum and refernum != expected_sn.strip():
        return None
    if (track.get("intro") or "").strip():
        return None
    return (
        "QIYUN 返回空轨迹（接口仅回显运单号，无 trackitem；"
        "请在 config QIYUN vendor 配置浏览器 Cookie/Session 后重试）"
    )


def _qiyun_parse_xml(text: str, expected_sn: str) -> tuple[list[CarrierTrackingLogEntry], str | None, str | None, str | None]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return [], None, None, f"QIYUN XML 解析失败: {exc}"
    track = _qiyun_find_track(root, expected_sn)
    if track is None:
        return [], None, None, "QIYUN API 未返回该单"
    logs, cid, tn = parse_qiyun_track_element(track, expected_sn=expected_sn)
    if not logs:
        hint = _qiyun_empty_track_hint(track, expected_sn)
        if hint:
            return [], cid, tn, hint
    return logs, cid, tn, None


def _qiyun_fetch_one(
    shipment_no: str,
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> tuple[list[CarrierTrackingLogEntry], str | None, str | None, str | None]:
    api_url = _qiyun_api_url(vendor)
    try:
        resp = requests.post(
            api_url,
            data=_qiyun_form_body(shipment_no, vendor),
            headers=_qiyun_request_headers(vendor),
            cookies=_qiyun_request_cookies(vendor),
            timeout=timeout,
            verify=_vendor_ssl_verify(vendor, default=True),
        )
        if resp.status_code >= 400:
            return [], None, None, f"HTTP {resp.status_code}"
        text = resp.content.decode(resp.encoding or "utf-8", errors="replace")
    except requests.RequestException as exc:
        return [], None, None, str(exc)
    if not (text or "").strip():
        return [], None, None, "QIYUN API 空响应"
    return _qiyun_parse_xml(text, shipment_no)


def fetch_qiyun_batch_for_rows(
    rows: list[dict[str, str]],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    """QIYUN：每单 POST form billid=运单号，响应 XML。"""
    out: dict[str, CarrierFetch] = {}
    for row in rows:
        sn = (row.get("shipment_no") or "").strip()
        if not sn:
            continue
        logs, cid, tn, err = _qiyun_fetch_one(sn, vendor, timeout=timeout)
        if err:
            out[sn] = ([], err, None, None)
            continue
        out[sn] = (logs, None, cid, tn)
        if log is not None:
            log(
                f"[承运商轨迹] {sn} QIYUN 返回 {len(logs)} 条"
                + (f"，carrier_id={cid}" if cid else "")
            )
    return out


def _tracklist_platform_key(vendor: dict[str, Any]) -> str:
    p = (vendor.get("platform") or detect_platform(vendor) or "olt").strip().lower()
    return p if p in ("olt", "haojie") else "olt"


def _tracklist_api_label(vendor: dict[str, Any]) -> str:
    return _tracklist_platform_key(vendor).upper()


def _tracklist_api_url(vendor: dict[str, Any]) -> str:
    explicit = (vendor.get("apiUrl") or "").strip()
    if explicit:
        return explicit
    if _tracklist_platform_key(vendor) == "haojie":
        return "http://120.24.174.13:8180/trackList"
    return "http://oa.olt56.com/trackList"


def _olt_request_headers(vendor: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }
    extra = vendor.get("headers")
    if isinstance(extra, dict):
        headers.update({str(k): str(v) for k, v in extra.items()})
    cookie_raw = (
        vendor.get("cookie")
        or vendor.get("Cookie")
        or vendor.get("cookies")
        or vendor.get("Cookies")
        or ""
    )
    cookie = cookie_raw.strip() if isinstance(cookie_raw, str) else ""
    if cookie and "Cookie" not in headers:
        headers["Cookie"] = cookie
    return headers


def _olt_request_cookies(vendor: dict[str, Any]) -> dict[str, str] | None:
    raw = vendor.get("cookies")
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return None


def _olt_search_fields(vendor: dict[str, Any]) -> str:
    return str(
        vendor.get("searchListField")
        or (
            "border.systemnumber,border.customernumber1,border.waybillnumber,"
            "border.tracknumber,border.newtracknumber,border.fbanumber"
        )
    )


def _olt_form_body(shipment_nos: list[str], vendor: dict[str, Any]) -> dict[str, str]:
    sep = str(vendor.get("noListSeparator") or "\n")
    limit = max(10, len(shipment_nos))
    if vendor.get("limit") is not None:
        limit = max(int(vendor["limit"]), len(shipment_nos))
    return {
        "page": str(vendor.get("page") if vendor.get("page") is not None else "1"),
        "limit": str(limit),
        "searchList.waybillnumber": sep.join(shipment_nos),
        "searchListField.waybillnumber": _olt_search_fields(vendor),
        "searchLang": str(vendor.get("searchLang") or vendor.get("language") or "zh"),
    }


def _olt_track_desc(item: dict[str, Any]) -> str:
    info = _maybe_repair_text((item.get("outinfo") or "").strip())
    desc = _maybe_repair_text((item.get("outdesc") or "").strip())
    country = _maybe_repair_text((item.get("countryname") or "").strip())
    if info and desc and info not in desc:
        text = f"{info}：{desc}"
    else:
        text = desc or info
    if country and country not in text:
        return f"{country} {text}".strip()
    return text


def _tracklist_event_id(item: dict[str, Any], vendor: dict[str, Any]) -> str | None:
    prefix = _tracklist_platform_key(vendor)
    pkid = item.get("pkid")
    if pkid is not None:
        return f"{prefix}:{pkid}"
    t = normalize_tracking_time(item.get("outdate") or "")
    return f"{prefix}:{t}" if t else None


def _olt_shipment_nos_from_item(item: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("customernumber1", "showcustomernumber1", "fbanumber"):
        v = (str(item.get(field) or "")).strip()
        if v:
            keys.add(v)
    return keys


def parse_olt_track_item(
    item: dict[str, Any],
    vendor: dict[str, Any] | None = None,
) -> tuple[list[CarrierTrackingLogEntry], str | None, str | None]:
    """trackList 系（OLT/HAOJIE）：customernumber1=运单号，systemnumber=carrier_id，showtracknumber=尾程单号。"""
    v = vendor or {"platform": "olt"}
    cid = (
        (str(item.get("systemnumber") or item.get("showsystemnumber") or item.get("waybillnumber") or ""))
        .strip()
        or None
    )
    tn = (
        (str(item.get("showtracknumber") or item.get("tracknumber") or item.get("shownewtracknumber") or ""))
        .strip()
        or None
    )
    logs: list[CarrierTrackingLogEntry] = []
    t = normalize_tracking_time(item.get("outdate") or "")
    d = _olt_track_desc(item)
    if t and d:
        logs.append(CarrierTrackingLogEntry.from_row(t, d, _tracklist_event_id(item, v)))
    return sort_logs_desc(logs), cid, tn


def _olt_post_track(
    shipment_nos: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int,
) -> tuple[list[dict[str, Any]], str | None]:
    api_url = _tracklist_api_url(vendor)
    label = _tracklist_api_label(vendor)
    try:
        resp = requests.post(
            api_url,
            data=_olt_form_body(shipment_nos, vendor),
            headers=_olt_request_headers(vendor),
            cookies=_olt_request_cookies(vendor),
            timeout=timeout,
            verify=_vendor_ssl_verify(vendor, default=True),
        )
        if resp.status_code >= 400:
            return [], f"HTTP {resp.status_code}"
        payload = _response_json(resp)
    except requests.RequestException as exc:
        return [], str(exc)
    if not isinstance(payload, dict):
        return [], f"{label} API 响应格式异常"
    code = payload.get("code")
    if code not in (0, "0"):
        msg = _maybe_repair_text(str(payload.get("msg") or payload.get("message") or ""))
        return [], msg or f"code={code}"
    data = payload.get("data")
    if not isinstance(data, list):
        return [], None
    return [x for x in data if isinstance(x, dict)], None


def fetch_tracklist_batch_for_rows(
    rows: list[dict[str, str]],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    """trackList 系批量（OLT/HAOJIE）：POST trackList，searchList.waybillnumber 换行分隔运单号。"""
    label = _tracklist_api_label(vendor)
    out: dict[str, CarrierFetch] = {}
    sn_to_row: dict[str, str] = {}
    for row in rows:
        sn = (row.get("shipment_no") or "").strip()
        if not sn:
            continue
        out[sn] = ([], None, None, None, None)
        sn_to_row[sn] = sn

    bills = list(sn_to_row.keys())
    if not bills:
        return out

    for i in range(0, len(bills), BATCH_SIZE):
        chunk = bills[i : i + BATCH_SIZE]
        groups, err = _olt_post_track(chunk, vendor, timeout=timeout)
        if err:
            for sn in chunk:
                out[sn] = ([], err, None, None)
            continue
        matched: set[str] = set()
        for item in groups:
            keys = _olt_shipment_nos_from_item(item)
            targets = {sn_to_row[k] for k in keys if k in sn_to_row}
            if not targets:
                continue
            logs, cid, tn = parse_olt_track_item(item, vendor)
            for sn in targets:
                out[sn] = (logs, None, cid, tn)
                matched.add(sn)
                if log is not None:
                    log(f"[承运商轨迹] {sn} 返回报文 {format_api_payload_for_log(item)}")
        for sn in chunk:
            if sn not in matched and out[sn][1] is None:
                out[sn] = ([], f"{label} API 未返回该单", None, None)
    return out


def fetch_olt_batch_for_rows(
    rows: list[dict[str, str]],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    return fetch_tracklist_batch_for_rows(rows, vendor, timeout=timeout, log=log)


def fetch_haojie_batch_for_rows(
    rows: list[dict[str, str]],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    return fetch_tracklist_batch_for_rows(rows, vendor, timeout=timeout, log=log)


def fetch_tracking_batch(
    tracking_numbers: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    """批量查询；返回 {运单号: (轨迹, 错误, carrier_id, tracking_number)}。"""
    cleaned = list(dict.fromkeys(n.strip() for n in tracking_numbers if n and n.strip()))
    if not cleaned:
        return {}
    platform = detect_platform(vendor)
    if platform == "topda":
        return _fetch_topda_batch(cleaned, vendor, timeout=timeout, log=log)
    if platform == "huawell_cms":
        return _fetch_huawell_cms_batch(cleaned, vendor, timeout=timeout)
    if platform == "txfba":
        rows = [{"shipment_no": n, "carrier_id": ""} for n in cleaned]
        return fetch_txfba_batch_for_rows(rows, vendor, timeout=timeout, log=log)
    if platform == "wy":
        rows = [{"shipment_no": n, "carrier_id": ""} for n in cleaned]
        return fetch_wy_batch_for_rows(rows, vendor, timeout=timeout, log=log)
    if platform == "yorky":
        rows = [{"shipment_no": n, "carrier_id": ""} for n in cleaned]
        return fetch_yorky_batch_for_rows(rows, vendor, timeout=timeout, log=log)
    if platform == "juren":
        rows = [{"shipment_no": n, "carrier_id": ""} for n in cleaned]
        return fetch_juren_batch_for_rows(rows, vendor, timeout=timeout, log=log)
    if platform == "qiyun":
        rows = [{"shipment_no": n, "carrier_id": ""} for n in cleaned]
        return fetch_qiyun_batch_for_rows(rows, vendor, timeout=timeout, log=log)
    if platform == "olt":
        rows = [{"shipment_no": n, "carrier_id": ""} for n in cleaned]
        return fetch_olt_batch_for_rows(rows, vendor, timeout=timeout, log=log)
    if platform == "haojie":
        rows = [{"shipment_no": n, "carrier_id": ""} for n in cleaned]
        return fetch_haojie_batch_for_rows(rows, vendor, timeout=timeout, log=log)
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
        return fetch_txfba_batch_for_rows(
            [{"shipment_no": sn, "carrier_id": ""}],
            vendor,
            timeout=timeout,
        ).get(sn, ([], "未返回", None, None))
    if platform == "wy":
        return fetch_wy_batch_for_rows(
            [{"shipment_no": sn, "carrier_id": ""}],
            vendor,
            timeout=timeout,
        ).get(sn, ([], "未返回", None, None))
    if platform == "yorky":
        return fetch_yorky_batch_for_rows(
            [{"shipment_no": sn, "carrier_id": ""}],
            vendor,
            timeout=timeout,
        ).get(sn, ([], "未返回", None, None))
    if platform == "juren":
        return fetch_juren_batch_for_rows(
            [{"shipment_no": sn, "carrier_id": ""}],
            vendor,
            timeout=timeout,
        ).get(sn, ([], "未返回", None, None))
    if platform == "qiyun":
        return fetch_qiyun_batch_for_rows(
            [{"shipment_no": sn, "carrier_id": ""}],
            vendor,
            timeout=timeout,
        ).get(sn, ([], "未返回", None, None))
    if platform == "olt":
        return fetch_olt_batch_for_rows(
            [{"shipment_no": sn, "carrier_id": ""}],
            vendor,
            timeout=timeout,
        ).get(sn, ([], "未返回", None, None))
    if platform == "haojie":
        return fetch_haojie_batch_for_rows(
            [{"shipment_no": sn, "carrier_id": ""}],
            vendor,
            timeout=timeout,
        ).get(sn, ([], "未返回", None, None))
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
        result = _response_json(resp)
    except Exception as exc:
        return _carrier_fail(str(exc))
    if not result.get("success"):
        return _carrier_fail(_maybe_repair_text(result.get("cnmessage") or "") or "承运商 API 返回失败")
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
        body = resp.content.lstrip()
        if "json" not in content_type and body.startswith(b"<"):
            return _carrier_fail("NextSLS 返回 HTML 而非 JSON，请检查 apiUrl 配置")
        result = _response_json(resp)
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
    """HWE CMS 批量轨迹：POST order_numbers。"""
    api_url = (vendor.get("apiUrl") or "").strip()
    if not api_url:
        return {n: ([], "HWE CMS 配置缺少 apiUrl", None, None, None) for n in tracking_numbers}
    uuid_val = (vendor.get("uuid") or vendor.get("UUID") or "").strip()
    body = {"order_numbers": tracking_numbers, "uuid": uuid_val}
    out: dict[str, CarrierFetch] = {n: ([], None, None, None, None) for n in tracking_numbers}
    try:
        resp = requests.post(api_url, json=body, timeout=timeout)
        resp.raise_for_status()
        payload = _response_json(resp)
    except Exception as exc:
        err = str(exc)
        return {n: ([], err, None, None, None) for n in tracking_numbers}
    if not isinstance(payload, list):
        return {n: ([], "HWE CMS 响应格式异常", None, None, None) for n in tracking_numbers}
    for item in payload:
        if not isinstance(item, dict):
            continue
        logs = sort_logs_desc(_normalize_details(item.get("details") or []))
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
                out[key] = (logs, None, cid or None, tn or None, None)
    return out


def _common_pack_ids_from_data(data: dict[str, Any]) -> tuple[str | None, str | None]:
    """XKP common_pack：orderno → carrier_id，zycode → 尾程 tracking_number。"""
    cid = (str(data.get("orderno") or "")).strip() or None
    tn = (str(data.get("zycode") or "")).strip() or None
    return cid, tn


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
        result = _response_json(resp)
    except Exception as exc:
        return _carrier_fail(str(exc))
    data = result.get("data") if isinstance(result, dict) else None
    if not data or "details" not in data:
        msg = _maybe_repair_text(result.get("msg") if isinstance(result, dict) else "") or "响应格式异常"
        return _carrier_fail(msg)
    carrier_id, outer_tn = _common_pack_ids_from_data(data)
    return _carrier_ok(
        _normalize_details(data.get("details") or []),
        carrier_id,
        outer_tn,
    )

def _fetch_topda_batch(
    tracking_numbers: list[str],
    vendor: dict[str, Any],
    *,
    timeout: int,
    log: LogFn | None = None,
) -> dict[str, CarrierFetch]:
    host = (vendor.get("host") or "topda.ai-ops.vip").strip()
    api_url = (vendor.get("apiUrl") or f"https://{host}/edi/pubTracking").strip()
    public_url = (vendor.get("publicUrl") or vendor.get("url") or "/public-tracking").strip()
    # 需要 subTrackings 子单号时设为 false（默认拉取子单）
    no_sub = vendor.get("noSubTracking", False)

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
    out: dict[str, CarrierFetch] = {n: ([], None, None, None, None) for n in tracking_numbers}
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        payload = _response_json(resp)
    except Exception as exc:
        err = str(exc)
        return {n: ([], err, None, None, None) for n in tracking_numbers}

    if not isinstance(payload, list):
        err = "Topda API 响应格式异常"
        return {n: ([], err, None, None, None) for n in tracking_numbers}

    for item in payload:
        if not isinstance(item, dict):
            continue
        logs = parse_topda_item(item)
        if item.get("notFound"):
            logs = []
        job_num, main_tn, all_tns = parse_topda_tracking_bundle(item)
        cid = job_num or _extract_carrier_id(item) or None
        tn = main_tn
        keys = _topda_item_keys(item)
        if not keys:
            continue
        for key in keys:
            if key in out:
                out[key] = (logs, None, cid, tn, all_tns or None)
                if log is not None:
                    log(
                        f"[承运商轨迹] {key} 返回报文 {format_api_payload_for_log(item)}"
                    )
    return out


