"""企业微信 @ 机器人：从消息解析运单号并查询本地运单状态。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..db.connection import get_database
from ..db.shipment_route_status import route_status_label
from ..db.shipments_repository import ShipmentsRepository
from .shipment_copy_format import (
    format_shipment_detail_summary_copy_text,
    format_shipment_tracking_numbers_copy_text,
)
from .wecom_aibot_shipment_refresh import (
    read_shipment_query_refresh_enabled,
    refresh_shipment_for_wecom_query,
)

_DETAIL_SUMMARY_HINT = "明细"
_TRACKING_COPY_HINT = "转单号"
_CARGO_HINT = "货箱"
_MARK_HINT = "唛头"
_MARK_SPLIT_HINT = "唛头拆分"
_PACKINGLIST_HINT = "箱单发票"
_WAREHOUSE_ENTRY_HINT = "进仓单"
# 长的在前，避免「唛头拆分」被先拆成「唛头」
_COMMAND_HINTS = (
    _PACKINGLIST_HINT,
    _WAREHOUSE_ENTRY_HINT,
    _TRACKING_COPY_HINT,
    _MARK_SPLIT_HINT,
    _MARK_HINT,
    _CARGO_HINT,
    _DETAIL_SUMMARY_HINT,
)

_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "config.json"

# 数字后紧贴中文时 \b 不会断开（中文也算 word）。
# 前面只排除字母，这样两票连写（…015DPSECO…）仍能拆开。
_SHIPMENT_NO_RE = re.compile(r"(?<![A-Za-z])(DPSECO\d+)", re.IGNORECASE)
_WAREHOUSE_ENTRY_PDF_RE = re.compile(r"进仓单\s*[（(]?\s*pdf", re.IGNORECASE)
_MARK_SPLIT_RE = re.compile(r"唛头\s*[（(]?\s*拆分\s*[)）]?")
_MAX_SHIPMENTS = 5
_FILE_MAX_SHIPMENTS = 50

_COARSE_STATUS_ZH: dict[str, str] = {
    "IN_TRANSIT": "转运中",
    "DELIVERED": "已签收",
    "INSPECTION": "查验",
    "UNKNOWN": "未知",
}


def _text_for_lookup(text: str) -> str:
    """去掉 @ 和指令词，避免「运单号唛头」被当成一个关键字。"""
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    cleaned = _MARK_SPLIT_RE.sub(" ", cleaned)
    for hint in _COMMAND_HINTS:
        cleaned = cleaned.replace(hint, " ")
    cleaned = re.sub(r"[（(]\s*pdf\s*[)）]?", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?<![A-Za-z0-9])pdf(?![A-Za-z0-9])", " ", cleaned, flags=re.IGNORECASE)
    return cleaned


def extract_lookup_keys(text: str, *, limit: int | None = None) -> list[str]:
    """从消息提取查询关键字：DPSECO 运单号、货件号、客户编号等（去 @ 提及和指令词）。"""
    cleaned = _text_for_lookup(text)
    if not cleaned.strip():
        return []
    cap = _MAX_SHIPMENTS if limit is None else max(1, limit)
    keys: list[str] = []
    for m in _SHIPMENT_NO_RE.findall(cleaned):
        upper = m.upper()
        if upper not in keys:
            keys.append(upper)
        if len(keys) >= cap:
            break
    seen_upper = {k.upper() for k in keys}
    if len(keys) < cap:
        for part in re.split(r"[\s,，、;；]+", cleaned):
            token = part.strip()
            if len(token) < 5:
                continue
            upper = token.upper()
            if upper in seen_upper:
                continue
            if any(no in upper for no in seen_upper if no.startswith("DPSECO")):
                continue
            keys.append(token)
            seen_upper.add(upper)
            if len(keys) >= cap:
                break
    return keys[:cap]


def extract_shipment_nos(text: str) -> list[str]:
    """兼容旧名；同 extract_lookup_keys。"""
    return extract_lookup_keys(text)


def message_wants_detail_summary(text: str) -> bool:
    """消息含「明细」时返回与列表「复制 → 运单明细」相同格式。"""
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    return _DETAIL_SUMMARY_HINT in cleaned


def message_wants_tracking_copy(text: str) -> bool:
    """消息含「转单号」时返回与列表「复制 → 转单号」相同格式。"""
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    return _TRACKING_COPY_HINT in cleaned


def message_wants_cargo_download(text: str) -> bool:
    """消息含「货箱」时下载货箱文件发回会话。"""
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    return _CARGO_HINT in cleaned


def message_wants_mark_split(text: str) -> bool:
    """消息含「唛头拆分」时按件数拆分单票唛头。"""
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    return _MARK_SPLIT_RE.search(cleaned) is not None


def message_wants_mark_download(text: str) -> bool:
    """消息含「唛头」时下载唛头文件发回会话。"""
    if message_wants_mark_split(text):
        return False
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    return _MARK_HINT in cleaned


def extract_mark_split_segments(text: str) -> list[int]:
    """取「唛头拆分」后面的件数，如「1 2 2」或「1,2,2」。"""
    from .mark_pdf_split import parse_mark_split_segments

    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    match = _MARK_SPLIT_RE.search(cleaned)
    if match is None:
        raise ValueError("请写「唛头拆分」，并在后面写件数，如：运单号 唛头拆分 1 2 2")
    tail = cleaned[match.end() :]
    numbers = [
        part
        for part in re.split(r"[\s,，、;；]+", tail)
        if re.fullmatch(r"\d+", part.strip() or "")
    ]
    if not numbers:
        raise ValueError("请在「唛头拆分」后写各工厂件数，用空格或逗号分隔，如：唛头拆分 1 2 2")
    return parse_mark_split_segments(" ".join(numbers))


def message_wants_packinglist_download(text: str) -> bool:
    """消息含「箱单发票」时下载箱单发票发回会话。"""
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    return _PACKINGLIST_HINT in cleaned


def message_wants_warehouse_entry_download(text: str) -> bool:
    """消息含「进仓单」时下载进仓单发回会话。"""
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    return _WAREHOUSE_ENTRY_HINT in cleaned


def message_wants_warehouse_entry_pdf(text: str) -> bool:
    """「进仓单PDF」或「进仓单（PDF）」时发 PDF，否则发 Excel。"""
    cleaned = re.sub(r"@\S+", " ", (text or "").strip())
    return _WAREHOUSE_ENTRY_PDF_RE.search(cleaned) is not None


def _resolve_wecom_download_ids(
    text: str,
    repo: ShipmentsRepository,
    *,
    label: str,
    require_waybill: bool = True,
) -> tuple[list[str], list[str]]:
    nos = extract_lookup_keys(text, limit=_FILE_MAX_SHIPMENTS)
    if not nos:
        raise ValueError(
            f"请发送运单号并加上「{label}」。多个运单号用空格或逗号分隔，关键词可以紧贴运单号。"
        )
    ids: list[str] = []
    notes: list[str] = []
    for no in nos:
        row = repo.get_by_lookup_priority(no)
        if row is None:
            notes.append(f"{no}：未找到运单")
            continue
        shipment_no = (row.get("shipmentNo") or no).strip()
        if require_waybill and not (row.get("waybillId") or "").strip():
            notes.append(f"{shipment_no}：无 DPS 运单 ID，请先更新运单")
            continue
        ids.append(str(row["id"]))
    if not ids:
        raise ValueError(f"{label}未生成。\n" + "\n".join(notes))
    return ids, notes


def build_wecom_cargo_file(text: str, repo: ShipmentsRepository | None = None) -> tuple[bytes, str, str]:
    """按消息里的单号生成货箱文件。返回 (内容, 文件名, 补充说明)。"""
    from .shipment_dps_cargo_download import build_dps_cargo_data_download

    if repo is None:
        repo = ShipmentsRepository(get_database(_DB_PATH))
    ids, notes = _resolve_wecom_download_ids(text, repo, label="货箱")
    content, _media_type, filename = build_dps_cargo_data_download(
        repo, _CONFIG_PATH, ids
    )
    return content, filename, "\n".join(notes)


def build_wecom_mark_file(text: str, repo: ShipmentsRepository | None = None) -> tuple[bytes, str, str]:
    """按消息里的单号生成唛头文件。返回 (内容, 文件名, 补充说明)。"""
    from .shipment_dps_mark_download import build_dps_mark_data_download

    if repo is None:
        repo = ShipmentsRepository(get_database(_DB_PATH))
    ids, notes = _resolve_wecom_download_ids(text, repo, label="唛头")
    content, _media_type, filename = build_dps_mark_data_download(
        repo, _CONFIG_PATH, ids
    )
    return content, filename, "\n".join(notes)


_WECOM_MARK_SPLIT_SEPARATE_MAX = 5


def wecom_mark_split_attachments(
    shipment_no: str,
    parts: list[tuple[str, bytes]],
    total_ctns: int,
) -> list[tuple[bytes, str]]:
    """5 份及以内逐个 PDF；超过 5 份打成一个压缩包。"""
    from .mark_pdf_split import zip_mark_split_files

    if len(parts) > _WECOM_MARK_SPLIT_SEPARATE_MAX:
        content, filename = zip_mark_split_files(
            shipment_no, parts, total_ctns=total_ctns
        )
        return [(content, filename)]
    return [(data, name) for name, data in parts]


def build_wecom_mark_split_files(
    text: str, repo: ShipmentsRepository | None = None
) -> tuple[list[tuple[bytes, str]], str]:
    """按「唛头拆分」后的件数拆分单票唛头。返回 ([(内容, 文件名)], 补充说明)。"""
    from .shipment_dps_mark_split_download import prepare_dps_mark_split_parts

    if repo is None:
        repo = ShipmentsRepository(get_database(_DB_PATH))
    nos = extract_lookup_keys(text, limit=_FILE_MAX_SHIPMENTS)
    if not nos:
        raise ValueError("请发送一个运单号，并在「唛头拆分」后写件数，如：运单号 唛头拆分 1 2 2")
    if len(nos) > 1:
        raise ValueError("唛头拆分只支持一票，请只发一个运单号。")
    segments = extract_mark_split_segments(text)
    ids, notes = _resolve_wecom_download_ids(text, repo, label="唛头拆分")
    if len(ids) != 1:
        raise ValueError("唛头拆分只支持一票，请只发一个运单号。")
    shipment_no, parts, total = prepare_dps_mark_split_parts(
        repo, _CONFIG_PATH, ids[0], segments
    )
    files = wecom_mark_split_attachments(shipment_no, parts, total)
    return files, "\n".join(notes)


def build_wecom_packinglist_file(text: str, repo: ShipmentsRepository | None = None) -> tuple[bytes, str, str]:
    """按消息里的单号生成箱单发票。返回 (内容, 文件名, 补充说明)。"""
    from .shipment_dps_packinglist_download import build_dps_packinglist_download

    if repo is None:
        repo = ShipmentsRepository(get_database(_DB_PATH))
    ids, notes = _resolve_wecom_download_ids(text, repo, label="箱单发票")
    content, _media_type, filename = build_dps_packinglist_download(
        repo, _CONFIG_PATH, ids
    )
    return content, filename, "\n".join(notes)


def _build_wecom_warehouse_entry_file(
    text: str,
    repo: ShipmentsRepository | None,
    *,
    pdf: bool,
) -> tuple[bytes, str, str]:
    from .shipment_dps_warehouse_entry_download import (
        build_dps_warehouse_entry_download,
        build_dps_warehouse_entry_pdf_download,
    )

    if repo is None:
        repo = ShipmentsRepository(get_database(_DB_PATH))
    ids, notes = _resolve_wecom_download_ids(
        text, repo, label="进仓单", require_waybill=False
    )
    builder = (
        build_dps_warehouse_entry_pdf_download
        if pdf
        else build_dps_warehouse_entry_download
    )
    content, _media_type, filename = builder(repo, _CONFIG_PATH, ids)
    return content, filename, "\n".join(notes)


def build_wecom_warehouse_entry_file(
    text: str, repo: ShipmentsRepository | None = None
) -> tuple[bytes, str, str]:
    """按消息里的单号生成进仓单 Excel。"""
    return _build_wecom_warehouse_entry_file(text, repo, pdf=False)


def build_wecom_warehouse_entry_pdf_file(
    text: str, repo: ShipmentsRepository | None = None
) -> tuple[bytes, str, str]:
    """按消息里的单号生成进仓单 PDF。"""
    return _build_wecom_warehouse_entry_file(text, repo, pdf=True)


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
    tracking_mode = message_wants_tracking_copy(text)
    detail_mode = message_wants_detail_summary(text) and not tracking_mode
    nos = extract_lookup_keys(text)
    if not nos:
        hint = (
            "请发送运单号（DPSECO…）、货件号或客户编号，多条可用空格/逗号分隔。"
        )
        if tracking_mode:
            hint += " 含「转单号」时返回与系统「复制 → 转单号」相同内容。"
        elif detail_mode:
            hint += " 含「明细」时返回与系统「复制 → 运单明细」相同内容。"
        return f"未识别到可查询单号。\n{hint}"
    if repo is None:
        repo = ShipmentsRepository(get_database(_DB_PATH))
    refresh = read_shipment_query_refresh_enabled(_CONFIG_PATH)
    if tracking_mode or detail_mode:
        formatter = (
            format_shipment_tracking_numbers_copy_text
            if tracking_mode
            else format_shipment_detail_summary_copy_text
        )
        blocks: list[str] = []
        for no in nos:
            # 与列表复制一致，只读本地字段，不拉 DPS / 轨迹
            row = _load_row_after_refresh(repo, no, refresh=False)
            if row:
                blocks.append(formatter([row]))
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
