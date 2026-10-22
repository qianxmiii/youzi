"""补货件号保存后，代发 config.json → dps_update_amz。"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from ..db.amz_update_port_rules import list_active_amz_port_rules
from ..db.connection import Database
from ..db.datetime_util import DATETIME_FMT, now_str
from ..db.shipments_repository import ShipmentsRepository
from .amz_port_resolve import resolve_amz_ports
from .shipment_query_config import load_config_json, resolve_dps_authorization

CONFIG_KEY = "dps_update_amz"
COOLDOWN_SEC = 60
DEFAULT_TIMEOUT = 30


def load_dps_update_amz_config(config_path: Path) -> dict[str, Any]:
    config = load_config_json(config_path)
    block = config.get(CONFIG_KEY)
    if not isinstance(block, dict):
        block = {}
    timeout = block.get("timeout") or DEFAULT_TIMEOUT
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    return {
        "url": (block.get("url") or "").strip(),
        "authorization": resolve_dps_authorization(config, block),
        "timeout": timeout,
    }


def _dps_business_error(response: requests.Response) -> str | None:
    """HTTP 成功时仍检查 DPS 业务 code。非 JSON 且 HTTP<400 视为成功。"""
    text = (response.text or "").strip()
    if not text:
        return None if response.status_code < 400 else f"HTTP {response.status_code}"
    try:
        body = response.json()
    except ValueError:
        if response.status_code >= 400:
            detail = text.replace("\n", " ")
            if len(detail) > 180:
                detail = detail[:180] + "…"
            return f"HTTP {response.status_code}：{detail}"
        return None
    if not isinstance(body, dict) or "code" not in body:
        return None if response.status_code < 400 else f"HTTP {response.status_code}"
    code = body.get("code")
    if code in (200, "200", 0, "0"):
        return None
    msg = str(body.get("msg") or body.get("message") or "").strip()
    if len(msg) > 180:
        msg = msg[:180] + "…"
    return msg or f"DPS code={code}"


def _chosen_port(override: Any, fallback: str | None) -> str | None:
    text = str(override or "").strip().upper()
    if text:
        return text
    fallback_text = (fallback or "").strip().upper()
    return fallback_text or None


def _cooldown_remaining(pushed_at: str | None) -> int:
    text = (pushed_at or "").strip()
    if not text:
        return 0
    try:
        pushed = datetime.strptime(text[:19], DATETIME_FMT)
    except ValueError:
        return 0
    elapsed = (datetime.now() - pushed).total_seconds()
    if elapsed < 0 or elapsed >= COOLDOWN_SEC:
        return 0
    return max(1, math.ceil(COOLDOWN_SEC - elapsed))


def _result(
    *,
    attempted: bool,
    ok: bool,
    skipped: bool,
    message: str,
    reason: str | None = None,
    origin_port: str | None = None,
    destination_port: str | None = None,
    retry_after_sec: int | None = None,
    transport_mode: str | None = None,
) -> dict[str, Any]:
    return {
        "attempted": attempted,
        "ok": ok,
        "skipped": skipped,
        "reason": reason,
        "message": message,
        "originPort": origin_port,
        "destinationPort": destination_port,
        "retryAfterSec": retry_after_sec,
        "transportMode": transport_mode,
    }


def preview_amz_push(
    database: Database,
    shipment: dict[str, Any],
    *,
    selected_dest_port: str | None = None,
) -> dict[str, Any]:
    with database.lock:
        rules = list_active_amz_port_rules(database.conn)
    resolved = resolve_amz_ports(
        rules,
        shipment,
        selected_dest_port=selected_dest_port,
    )
    remaining = _cooldown_remaining(shipment.get("amzPushAt"))
    message = resolved["message"]
    if remaining:
        extra = f"距上次推送还需等待 {remaining} 秒"
        message = f"{message}；{extra}" if message else extra
    return _result(
        attempted=False,
        ok=bool(resolved["ok"]) and remaining == 0,
        skipped=not resolved["ok"] or remaining > 0,
        reason="rate_limit" if remaining else (None if resolved["ok"] else "port"),
        message=message,
        origin_port=resolved["originPort"],
        destination_port=resolved["destinationPort"],
        retry_after_sec=remaining or None,
        transport_mode=resolved["transportMode"],
    )


def push_amz_update(
    database: Database,
    shipments_repo: ShipmentsRepository,
    config_path: Path,
    shipment: dict[str, Any],
) -> dict[str, Any]:
    """本地已保存后调用。未真正发出请求时不占用冷却。"""
    shipment_id = (shipment.get("customerShipmentId") or "").strip()
    if not shipment_id:
        return _result(attempted=False, ok=False, skipped=True, reason="no_shipment_id", message="货件号为空，未推送")
    waybill_id = (shipment.get("waybillId") or "").strip()
    if not waybill_id:
        return _result(attempted=False, ok=False, skipped=True, reason="no_waybill", message="缺少 DPS 运单 ID，未推送")

    with database.lock:
        rules = list_active_amz_port_rules(database.conn)
    resolved = resolve_amz_ports(rules, shipment)
    origin_port = _chosen_port(shipment.get("amzPushOriginPort"), resolved["originPort"])
    destination_port = _chosen_port(shipment.get("amzPushDestPort"), resolved["destinationPort"])
    if not origin_port or not destination_port:
        return _result(
            attempted=False,
            ok=False,
            skipped=True,
            reason="port",
            message=resolved["message"] or "起运港或目的港为空，未推送",
            origin_port=origin_port,
            destination_port=destination_port,
            transport_mode=resolved["transportMode"],
        )

    remaining = _cooldown_remaining(shipment.get("amzPushAt"))
    if remaining:
        return _result(
            attempted=False,
            ok=False,
            skipped=True,
            reason="rate_limit",
            message=f"这一票 1 分钟内已推送过，请 {remaining} 秒后再试",
            origin_port=origin_port,
            destination_port=destination_port,
            retry_after_sec=remaining,
            transport_mode=resolved["transportMode"],
        )

    cfg = load_dps_update_amz_config(config_path)
    if not cfg["url"] or not cfg["authorization"]:
        return _result(
            attempted=False,
            ok=False,
            skipped=True,
            reason="config",
            message="未配置 dps_update_amz.url 或 dps_authorization，未推送",
            origin_port=origin_port,
            destination_port=destination_port,
            transport_mode=resolved["transportMode"],
        )

    body = {
        "orderId": waybill_id,
        "shipmentId": shipment_id,
        "referenceId": (shipment.get("amazonRefId") or "").strip(),
        "originPort": origin_port,
        "destinationPort": destination_port,
        "type": "1",
    }
    shipments_repo.touch_amz_push_at(str(shipment["id"]), now_str())
    try:
        response = requests.post(
            cfg["url"],
            json=body,
            headers={
                "Authorization": cfg["authorization"],
                "Content-Type": "application/json",
            },
            timeout=cfg["timeout"],
        )
    except requests.RequestException as exc:
        return _result(
            attempted=True,
            ok=False,
            skipped=False,
            reason="dps",
            message=f"推送失败：{exc.__class__.__name__}",
            origin_port=origin_port,
            destination_port=destination_port,
            retry_after_sec=COOLDOWN_SEC,
            transport_mode=resolved["transportMode"],
        )

    business_error = _dps_business_error(response)
    if response.status_code >= 400 or business_error:
        message = business_error or f"推送失败（HTTP {response.status_code}）"
        if response.status_code >= 400 and business_error:
            message = f"HTTP {response.status_code}：{business_error}"
        return _result(
            attempted=True,
            ok=False,
            skipped=False,
            reason="dps",
            message=message,
            origin_port=origin_port,
            destination_port=destination_port,
            retry_after_sec=COOLDOWN_SEC,
            transport_mode=resolved["transportMode"],
        )

    note = resolved["message"]
    message = "已推送到亚马逊"
    if note:
        message = f"{message}（{note}）"
    return _result(
        attempted=True,
        ok=True,
        skipped=False,
        message=message,
        origin_port=origin_port,
        destination_port=destination_port,
        retry_after_sec=COOLDOWN_SEC,
        transport_mode=resolved["transportMode"],
    )
