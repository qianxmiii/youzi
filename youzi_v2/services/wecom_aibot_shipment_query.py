"""企业微信 @ 机器人：从消息解析运单号并查询本地运单状态。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..db.connection import get_database
from ..db.shipment_route_status import route_status_label
from ..db.shipments_repository import ShipmentsRepository
from .shipment_copy_format import format_shipment_detail_summary_copy_text
from .wecom_aibot_shipment_refresh import (
    read_shipment_query_refresh_enabled,
    refresh_shipment_for_wecom_query,
)

_DETAIL_SUMMARY_HINT = "明细"

_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "config.json"

# 与 DPS 运单号常见格式一致；上限避免刷屏
_SHIPMENT_NO_RE = re.compile(r"\b(DPSECO\d+)\b", re.IGNORECASE)
_MAX_SHIPMENTS = 5

_COARSE_STATUS_ZH: dict[str, str] = {
    "IN_TRANSIT": "转运中",
    "DELIVERED": "已签收",
    "INSPECTION": "查验",
    "UNKNOWN": "未知",
}


def extract_lookup_keys(text: str) -> list[str]:
    """从消息提取查询关键字：DPSECO 运单号、货件号、客户编号等（去 @ 提及）。"""
    raw = (text or "").strip()
    if not raw:
        return []
    cleaned = re.sub(r"@\S+", " ", raw)
    keys: list[str] = []
    for m in _SHIPMENT_NO_RE.findall(cleaned):
        upper = m.upper()
        if upper not in keys:
            keys.append(upper)
    seen_upper = {k.upper() for k in keys}
    for part in re.split(r"[\s,，、;；]+", cleaned):
        token = part.strip()
        if len(token) < 5:
            continue
        if token.upper() in seen_upper:
            continue
        keys.append(token)
        seen_upper.add(token.upper())
        if len(keys) >= _MAX_SHIPMENTS:
            break
    return keys[:_MAX_SHIPMENTS]


def extract_shipment_nos(text: str) -> list[str]:
    """兼容旧名；同 extract_lookup_keys。"""
    return extract_lookup_keys(text)


def message_wants_detail_summary(text: str) -> bool:
    """消息含「明细」时返回与列表「复制 → 运单明细」相同格式。"""
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    return _DETAIL_SUMMARY_HINT in cleaned


def _raw(value: Any) -> str:
    return (str(value).strip() if value is not None else "")


def _format_time(value: Any) -> str:
    s = _raw(value)
    if not s:
        return ""
    if len(s) >= 16:
        return s[:16]
    return s


def _optional_line(label: str, value: Any, *, format_value: Any = None) -> str | None:
    if format_value is not None:
        text = format_value(value)
    else:
        text = _raw(value)
    if not text:
        return None
    return f"{label}{text}"


def _norm_key(value: Any) -> str:
    return (str(value).strip() if value is not None else "").upper()


def _customer_ref_lines(row: dict[str, Any]) -> list[str]:
    """客户编号与货件号相同时只展示货件号。"""
    customer_no = (row.get("customerNo") or "").strip()
    shipment_id = (row.get("customerShipmentId") or "").strip()
    if customer_no and shipment_id and _norm_key(customer_no) == _norm_key(shipment_id):
        return [f"货件号：{shipment_id}"]
    lines: list[str] = []
    if customer_no:
        lines.append(f"客户编号：{customer_no}")
    if shipment_id:
        lines.append(f"货件号：{shipment_id}")
    return lines


def _channel_text(row: dict[str, Any]) -> str:
    zh = (row.get("channelNameZh") or "").strip()
    if zh:
        return zh
    return _raw(row.get("channelCode"))


def _coarse_status_text(row: dict[str, Any]) -> str:
    coarse_code = (row.get("statusCode") or "").strip().upper()
    if not coarse_code:
        return ""
    return _COARSE_STATUS_ZH.get(coarse_code, coarse_code)


def _route_status_text(row: dict[str, Any]) -> str:
    label = route_status_label(row.get("routeStatus"))
    if label:
        return label
    return _raw(row.get("routeStatus"))


def format_shipment_status_block(row: dict[str, Any]) -> str:
    sn = _raw(row.get("shipmentNo")) or "—"
    lines: list[str] = [f"【{sn}】"]
    for part in (
        _optional_line("客户：", row.get("customer")),
        *(_customer_ref_lines(row)),
        _optional_line("渠道：", _channel_text(row)),
        _optional_line("转运状态：", _coarse_status_text(row)),
        _optional_line("明细状态：", _route_status_text(row)),
        _optional_line("最新内部轨迹：", row.get("latestTrackingDesc")),
        _optional_line("轨迹时间：", row.get("latestTrackingTime"), format_value=_format_time),
        _optional_line("最新承运商轨迹：", row.get("latestCarrierDesc")),
        _optional_line("轨迹时间：", row.get("latestCarrierTime"), format_value=_format_time),
        _optional_line("派送仓库：", row.get("addressCode")),
        _optional_line("邮编：", row.get("zipcode")),
        _optional_line("件数：", row.get("ctns"), format_value=lambda v: str(v) if v is not None else ""),
        _optional_line("转单号：", row.get("trackingNumber")),
    ):
        if part:
            lines.append(part)
    return "\n".join(lines)


def _load_row_after_refresh(
    repo: ShipmentsRepository,
    lookup_no: str,
    *,
    refresh: bool,
) -> dict[str, Any] | None:
    row = repo.get_by_lookup_priority(lookup_no)
    if not row:
        return None
    shipment_no = (row.get("shipmentNo") or "").strip()
    if refresh and shipment_no and read_shipment_query_refresh_enabled(_CONFIG_PATH):
        refresh_shipment_for_wecom_query(shipment_no, config_path=_CONFIG_PATH)
        row = repo.get_by_shipment_no(shipment_no) or row
    return row


def build_shipment_query_reply(text: str, repo: ShipmentsRepository | None = None) -> str:
    detail_mode = message_wants_detail_summary(text)
    nos = extract_lookup_keys(text)
    if not nos:
        hint = (
            "请发送运单号（DPSECO…）、货件号或客户编号，多条可用空格/逗号分隔。"
        )
        if detail_mode:
            hint += " 含「明细」时返回与系统「复制 → 运单明细」相同内容。"
        return f"未识别到可查询单号。\n{hint}"
    if repo is None:
        repo = ShipmentsRepository(get_database(_DB_PATH))
    refresh = read_shipment_query_refresh_enabled(_CONFIG_PATH)
    if detail_mode:
        blocks: list[str] = []
        for no in nos:
            # 运单明细摘要仅读库字段，不拉 DPS 明细状态/轨迹
            row = _load_row_after_refresh(repo, no, refresh=False)
            if row:
                blocks.append(format_shipment_detail_summary_copy_text([row]))
            else:
                blocks.append(f"【{no}】\n未找到运单（已依次尝试运单号→货件号→客户编号）。")
        if len(nos) >= _MAX_SHIPMENTS:
            blocks.append(f"（仅展示前 {_MAX_SHIPMENTS} 个单号）")
        return "\n\n".join(blocks)

    blocks: list[str] = []
    for no in nos:
        row = _load_row_after_refresh(repo, no, refresh=refresh)
        if row:
            blocks.append(format_shipment_status_block(row))
        else:
            blocks.append(f"【{no}】\n未找到运单（已依次尝试运单号→货件号→客户编号）。")
    if len(nos) >= _MAX_SHIPMENTS:
        blocks.append(f"（仅展示前 {_MAX_SHIPMENTS} 个单号）")
    return "\n\n".join(blocks)


def extract_callback_text(frame: dict[str, Any]) -> str | None:
    body = frame.get("body") if isinstance(frame.get("body"), dict) else {}
    if body.get("compat_info"):
        return None
    msgtype = (body.get("msgtype") or "").strip().lower()
    if msgtype == "text":
        text_body = body.get("text") if isinstance(body.get("text"), dict) else {}
        content = (text_body.get("content") or "").strip()
        return content or None
    if msgtype == "mixed":
        mixed = body.get("mixed") if isinstance(body.get("mixed"), dict) else {}
        items = mixed.get("msg_item") if isinstance(mixed.get("msg_item"), list) else []
        parts: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if (item.get("msgtype") or "").lower() == "text":
                tb = item.get("text") if isinstance(item.get("text"), dict) else {}
                part = (tb.get("content") or "").strip()
                if part:
                    parts.append(part)
        joined = " ".join(parts).strip()
        return joined or None
    return None
