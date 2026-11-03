"""把日常报价原文解析成仓点、渠道行和整票合计。不写库。"""

from __future__ import annotations

import re
from typing import Any

_TO_RE = re.compile(r"^To\s+([A-Za-z0-9]+)\s*[,，]?\s*(.*)$", re.IGNORECASE)
_CHANNEL_RE = re.compile(
    r"^(?P<term>DDP|DDU)\s+(?P<channel>.+?)\s*:\s*"
    r"(?P<unit>\d+(?:\.\d+)?)\s*(?P<currency>usd|rmb|cny)\s*/\s*(?P<basis>kg|cbm)\s*\*\s*"
    r"(?P<charge>\d+(?:\.\d+)?)\s*(?:kg|cbm)\s*=\s*"
    r"(?P<total>\d+(?:\.\d+)?)\s*(?:usd|rmb|cny)"
    r"(?:\s+(?P<dmin>\d+)\s*-\s*(?P<dmax>\d+)\s*days)?"
    r"(?P<rest>.*)$",
    re.IGNORECASE,
)
_PICKUP_RE = re.compile(
    r"^(?:pickup\s*fee|提货费)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*([A-Za-z]{3})?\s*$",
    re.IGNORECASE,
)
_CTNS_RE = re.compile(r"(\d+)\s*ctns?\b", re.IGNORECASE)
_KG_RE = re.compile(r"(\d+(?:\.\d+)?)\s*kg\b", re.IGNORECASE)
_CBM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*cbm\b", re.IGNORECASE)
_SPLIT_RE = re.compile(r"^-{3,}\s*$")


def _cargo(text: str) -> dict[str, int | float | None]:
    ctns = _CTNS_RE.search(text or "")
    kg = _KG_RE.search(text or "")
    cbm = _CBM_RE.search(text or "")
    return {
        "ctns": int(ctns.group(1)) if ctns else None,
        "weightKg": float(kg.group(1)) if kg else None,
        "volumeCbm": float(cbm.group(1)) if cbm else None,
    }


def _currency_code(value: str) -> str:
    code = (value or "USD").strip().upper()
    return "CNY" if code == "RMB" else code


def _has_cargo(text: str) -> bool:
    cargo = _cargo(text)
    return any(cargo[key] is not None for key in ("ctns", "weightKg", "volumeCbm"))


def parse_quote_paste(text: str) -> dict[str, Any]:
    destinations: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    summary_mode = False
    summary = {"ctns": None, "weightKg": None, "volumeCbm": None}
    pickup_fee: float | None = None
    pickup_currency = ""
    unrecognized: list[str] = []

    def close_current() -> None:
        nonlocal current
        if current is not None:
            destinations.append(current)
            current = None

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if _SPLIT_RE.match(line):
            close_current()
            summary_mode = True
            continue
        pickup = _PICKUP_RE.match(line)
        if pickup:
            close_current()
            pickup_fee = float(pickup.group(1))
            pickup_currency = (pickup.group(2) or "USD").upper()
            if pickup_currency == "RMB":
                pickup_currency = "CNY"
            continue
        if summary_mode:
            if _has_cargo(line) and summary["ctns"] is None and summary["weightKg"] is None:
                summary = _cargo(line)
                continue
            unrecognized.append(line)
            continue
        to_match = _TO_RE.match(line)
        if to_match:
            close_current()
            cargo = _cargo(to_match.group(2))
            current = {
                "addressCode": to_match.group(1).upper(),
                "ctns": cargo["ctns"],
                "weightKg": cargo["weightKg"],
                "volumeCbm": cargo["volumeCbm"],
                "channels": [],
            }
            continue
        channel = _CHANNEL_RE.match(line)
        if channel and current is not None:
            rest = (channel.group("rest") or "").strip()
            current["channels"].append(
                {
                    "tradeTerm": channel.group("term").upper(),
                    "channelName": re.sub(r"\s+", " ", channel.group("channel")).strip(),
                    "unitPrice": float(channel.group("unit")),
                    "chargeWeightKg": float(channel.group("charge")),
                    "quotedAmount": float(channel.group("total")),
                    "quotedCurrency": _currency_code(channel.group("currency")),
                    "priceBasis": channel.group("basis").lower(),
                    "transitDaysMin": int(channel.group("dmin")) if channel.group("dmin") else None,
                    "transitDaysMax": int(channel.group("dmax")) if channel.group("dmax") else None,
                    "note": rest,
                }
            )
            continue
        unrecognized.append(line)
    close_current()
    return {
        "destinations": destinations,
        "summaryCtns": summary["ctns"],
        "summaryWeightKg": summary["weightKg"],
        "summaryVolumeCbm": summary["volumeCbm"],
        "pickupFee": pickup_fee,
        "pickupFeeCurrency": pickup_currency,
        "unrecognized": unrecognized,
    }
