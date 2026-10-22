"""按 amz_update_port_rules 解析推送给 DPS 的起运港、目的港。"""

from __future__ import annotations

from typing import Any

_SEA_KEYWORD_FIELDS = (
    "destinationPortCode",
    "deliveryAddress",
    "addressCode",
    "channelNameZh",
)


def transport_mode_for_category(category: str | None) -> tuple[str, bool]:
    """返回 (AIR|SEA, 类别是否缺失)。缺失时按海运，并标记不确定。"""
    text = (category or "").strip()
    if not text:
        return "SEA", True
    if text == "空运":
        return "AIR", False
    return "SEA", False


def _match(
    rules: list[dict[str, Any]],
    *,
    mode: str,
    country: str,
    leg: str,
    kind: str,
) -> list[dict[str, Any]]:
    country_key = (country or "").strip().upper()
    return [
        row
        for row in rules
        if row["transportMode"] == mode
        and row["leg"] == leg
        and row["ruleKind"] == kind
        and row["countryCode"] == country_key
        and row["portCode"]
    ]


def _default_port(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    defaults = [row for row in rows if row["isDefault"]]
    picked = defaults or rows
    picked.sort(key=lambda row: (row["sortOrder"], row["code"]))
    return picked[0]["portCode"]


def resolve_amz_ports(
    rules: list[dict[str, Any]],
    shipment: dict[str, Any],
    *,
    selected_dest_port: str | None = None,
) -> dict[str, Any]:
    mode, uncertain = transport_mode_for_category(shipment.get("channelCategory"))
    country = (shipment.get("countryCode") or "").strip().upper()
    notes: list[str] = []
    if uncertain:
        notes.append("渠道类别为空，按海运港口规则推送")

    origin = _resolve_origin(rules, shipment, mode)
    dest, dest_error = _resolve_destination(
        rules,
        shipment,
        mode=mode,
        country=country,
        selected_dest_port=selected_dest_port,
    )
    errors: list[str] = []
    if not origin:
        if mode == "AIR":
            errors.append("未配置空运起运港")
        else:
            errors.append("收货仓不是「深圳仓」或「义乌仓」，无法确定海运起运港")
    if dest_error:
        errors.append(dest_error)
    elif not dest:
        errors.append("无法确定目的港")
    return {
        "transportMode": mode,
        "modeUncertain": uncertain,
        "originPort": origin,
        "destinationPort": dest,
        "ok": not errors,
        "message": "；".join([*notes, *errors]) if errors or notes else "",
    }


def _resolve_origin(
    rules: list[dict[str, Any]],
    shipment: dict[str, Any],
    mode: str,
) -> str | None:
    if mode == "AIR":
        return _default_port(_match(rules, mode="AIR", country="CN", leg="ORIGIN", kind="DEFAULT"))
    warehouse = (shipment.get("originWarehouseCode") or "").strip()
    for row in _match(rules, mode="SEA", country="CN", leg="ORIGIN", kind="ORIGIN_EXACT"):
        if row["matchText"] and row["matchText"] == warehouse:
            return row["portCode"]
    return None


def _resolve_destination(
    rules: list[dict[str, Any]],
    shipment: dict[str, Any],
    *,
    mode: str,
    country: str,
    selected_dest_port: str | None,
) -> tuple[str | None, str | None]:
    if mode == "AIR" and country in {"US", "CA"}:
        options = _match(rules, mode="AIR", country=country, leg="DESTINATION", kind="OPTION")
        codes = {row["portCode"] for row in options}
        chosen = (selected_dest_port or shipment.get("amzPushDestPort") or "").strip().upper()
        if chosen and chosen in codes:
            return chosen, None
        fallback = _default_port(options)
        if fallback:
            return fallback, None
        return None, f"未配置{country}空运目的港选项"
    if mode == "AIR":
        port = _default_port(
            _match(rules, mode="AIR", country=country, leg="DESTINATION", kind="DEFAULT")
        )
        if port:
            return port, None
        return None, f"未配置{country or '空'}空运目的港"
    if country == "US":
        keywords = _match(rules, mode="SEA", country="US", leg="DESTINATION", kind="DEST_KEYWORD")
        keywords.sort(key=lambda row: (row["sortOrder"], row["code"]))
        for field in _SEA_KEYWORD_FIELDS:
            text = str(shipment.get(field) or "")
            if not text:
                continue
            for row in keywords:
                word = row["matchText"]
                if word and word in text:
                    return row["portCode"], None
    port = _default_port(
        _match(rules, mode="SEA", country=country, leg="DESTINATION", kind="DEFAULT")
    )
    if port:
        return port, None
    return None, f"未配置{country or '空'}海运目的港"
