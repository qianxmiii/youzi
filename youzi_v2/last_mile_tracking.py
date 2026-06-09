"""尾程转单号规范化：剥离 UPS/FedEx 等快递公司前缀后再入库。"""

from __future__ import annotations

import re
from typing import Literal

LastMileCarrierHint = Literal["ups", "fedex", "usps", "dhl", "conwest", "dpd"]

# 运单 express_code 存库用大写：UPS / FEDEX / DPD / CWE（及 USPS / DHL）
CANONICAL_EXPRESS_CODES: frozenset[str] = frozenset(
    {"UPS", "FEDEX", "DPD", "CWE", "USPS", "DHL"}
)

_EXPRESS_CODE_TO_HINT: dict[str, LastMileCarrierHint] = {
    "UPS": "ups",
    "FEDEX": "fedex",
    "FDX": "fedex",
    "DPD": "dpd",
    "DPDUK": "dpd",
    "CWE": "conwest",
    "CONWEST": "conwest",
    "USPS": "usps",
    "DHL": "dhl",
}

# 「UPS 1Z…」「CWE C03IK…」等
_PREFIX_WITH_SEP = re.compile(
    r"^(?P<prefix>UPS|FED\s*EX|FEDEX|FDX|USPS|DHL|CWE|DPDUK|DPD)\s*[-#:：]?\s*(?P<number>.+)$",
    re.IGNORECASE,
)
# 「UPS1Z…」无空格（单号足够长才剥离，避免误伤）
_PREFIX_COMPACT = re.compile(
    r"^(?P<prefix>UPS|FEDEX|FDX|USPS|DHL|CWE|DPDUK|DPD)(?P<number>.+)$",
    re.IGNORECASE,
)

_CONWEST_TRACKING_RE = re.compile(r"^C03[A-Z]{2}\d{12,}$", re.IGNORECASE)
CONWEST_SUFFIX_LEN = 5
CONWEST_17TRACK_MAX = 40
CONWEST_17TRACK_FC = "100467"

_PREFIX_TO_HINT: dict[str, LastMileCarrierHint] = {
    "UPS": "ups",
    "FEDEX": "fedex",
    "FDX": "fedex",
    "USPS": "usps",
    "DHL": "dhl",
}


def _prefix_to_hint(prefix: str) -> LastMileCarrierHint | None:
    key = prefix.upper().replace(" ", "")
    if key.startswith("FED"):
        return "fedex"
    if key == "CWE":
        return "conwest"
    if key.startswith("DPD"):
        return "dpd"
    return _PREFIX_TO_HINT.get(key)


def is_conwest_tracking_number(number: str | None) -> bool:
    tn = (number or "").strip().upper().replace(" ", "")
    return bool(tn and _CONWEST_TRACKING_RE.match(tn))


def expand_conwest_tracking_numbers(
    seed: str | None,
    count: int | None,
) -> list[str]:
    """
    Conwest 单号按件数展开：C03IK469759415360001 + 40 件 → …60001 … …60040。
    末 5 位为流水号。
    """
    tn = (normalize_tracking_field_value(seed) or (seed or "").strip()).upper().replace(" ", "")
    if not tn:
        return []
    if not is_conwest_tracking_number(tn):
        return [tn]
    pieces = max(1, int(count or 1))
    if pieces == 1:
        return [tn]
    if len(tn) <= CONWEST_SUFFIX_LEN:
        return [tn]
    prefix = tn[:-CONWEST_SUFFIX_LEN]
    try:
        start = int(tn[-CONWEST_SUFFIX_LEN :])
    except ValueError:
        return [tn]
    return [f"{prefix}{start + i:05d}" for i in range(pieces)]


def resolve_conwest_writeback(
    seed: str | None,
    ctns: int | None,
) -> tuple[str | None, list[str]]:
    nums = expand_conwest_tracking_numbers(seed, ctns)
    if not nums:
        return None, []
    return nums[0], nums


def build_conwest_17track_url(numbers: list[str]) -> str | None:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in numbers:
        n = normalize_tracking_field_value(raw) or (raw or "").strip()
        if n and n not in seen:
            seen.add(n)
            cleaned.append(n)
    if not cleaned:
        return None
    batch = cleaned[:CONWEST_17TRACK_MAX]
    nums_param = ",".join(batch)
    return f"https://t.17track.net/en#nums={nums_param}&fc={CONWEST_17TRACK_FC}"


def normalize_express_code(raw: str | None) -> str | None:
    """入库/更新：规范为 UPS/FEDEX/DPD/CWE 等；空或无法识别则 None（走自动识别）。"""
    text = (raw or "").strip().upper().replace(" ", "")
    if not text:
        return None
    if text in ("AUTO", "自动", "自动识别"):
        return None
    if text.startswith("FED"):
        return "FEDEX"
    if text in ("CONWEST",):
        return "CWE"
    if text in CANONICAL_EXPRESS_CODES:
        return text
    return None


def express_code_to_carrier_hint(express_code: str | None) -> LastMileCarrierHint | None:
    key = (express_code or "").strip().upper().replace(" ", "")
    if not key:
        return None
    return _EXPRESS_CODE_TO_HINT.get(key)


def infer_last_mile_carrier_hint(number: str) -> LastMileCarrierHint | None:
    """按单号形态推断承运商（入库/展示辅助）。"""
    tn = (number or "").strip().upper().replace(" ", "")
    if not tn:
        return None
    if tn.startswith("1Z") and len(tn) >= 18:
        return "ups"
    if _CONWEST_TRACKING_RE.match(tn):
        return "conwest"
    if re.match(r"^DPD(UK)?", tn):
        return "dpd"
    if re.match(r"^00\d{8,}$", tn):
        return "dhl"
    return None


def normalize_last_mile_tracking_number(
    raw: str | None,
) -> tuple[str, LastMileCarrierHint | None]:
    """
    解析带快递公司前缀的尾程单号。
    返回 (纯单号, 承运商提示)；无内容时 ('', None)。
    """
    text = (raw or "").strip()
    if not text:
        return "", None

    m = _PREFIX_WITH_SEP.match(text)
    if m:
        number = (m.group("number") or "").strip()
        hint = _prefix_to_hint(m.group("prefix") or "")
        return (number or text, hint)

    compact = _PREFIX_COMPACT.match(text.replace(" ", ""))
    if compact:
        number = (compact.group("number") or "").strip()
        if len(number) >= 8:
            hint = _prefix_to_hint(compact.group("prefix") or "")
            return (number, hint)

    hint = infer_last_mile_carrier_hint(text)
    return text, hint


def normalize_tracking_field_value(raw: str | None) -> str | None:
    """入库用：剥离前缀；空则 None。"""
    number, _ = normalize_last_mile_tracking_number(raw)
    cleaned = number.strip()
    return cleaned if cleaned else None
