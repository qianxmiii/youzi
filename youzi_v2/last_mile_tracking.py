"""尾程转单号规范化：剥离 UPS/FedEx 等快递公司前缀后再入库。"""

from __future__ import annotations

import re
from typing import Any, Literal

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

# 「UPS 1Z…」「CWE C03IK…」等（整段输入）
_PREFIX_WITH_SEP = re.compile(
    r"^(?P<prefix>UPS|FED\s*EX|FEDEX|FDX|USPS|DHL|CWE|DPDUK|DPD)\s*[-#:：]?\s*(?P<number>.+)$",
    re.IGNORECASE,
)
# 「UPS1Z…」无空格（单号足够长才剥离，避免误伤）
_PREFIX_COMPACT = re.compile(
    r"^(?P<prefix>UPS|FEDEX|FDX|USPS|DHL|CWE|DPDUK|DPD)(?P<number>.+)$",
    re.IGNORECASE,
)
# 轨迹正文中的「FedEx 8776…」（可出现在句子任意位置）
_IN_TEXT_LAST_MILE_RE = re.compile(
    r"(?P<prefix>UPS|FED\s*EX|FEDEX|FDX|USPS|DHL|CWE|DPDUK|DPD)\s*[-#:：]?\s*"
    r"(?P<number>[A-Za-z0-9]{8,30})",
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


def carrier_hint_to_express_code(hint: LastMileCarrierHint | None) -> str | None:
    if not hint:
        return None
    mapping: dict[LastMileCarrierHint, str] = {
        "ups": "UPS",
        "fedex": "FEDEX",
        "dpd": "DPD",
        "conwest": "CWE",
        "usps": "USPS",
        "dhl": "DHL",
    }
    return mapping.get(hint)


def _is_plausible_last_mile_number(number: str, hint: LastMileCarrierHint) -> bool:
    tn = (number or "").strip().upper().replace(" ", "")
    if len(tn) < 8:
        return False
    if hint == "fedex":
        return tn.isdigit() and 10 <= len(tn) <= 15
    if hint == "ups":
        return tn.startswith("1Z") and len(tn) >= 10
    if hint == "dhl":
        return tn.isdigit() and len(tn) >= 10
    if hint == "dpd":
        return tn.isdigit() and len(tn) >= 10
    if hint == "conwest":
        return is_conwest_tracking_number(tn) or (tn.startswith("C") and len(tn) >= 10)
    if hint == "usps":
        return len(tn) >= 10
    return True


def extract_last_mile_from_track_desc(
    desc: str | None,
) -> tuple[str, LastMileCarrierHint] | None:
    """从轨迹正文识别「承运商 + 单号」（如 FedEx 877617962361）。

    需同时具备承运商标签与合法单号；同一条描述多处命中时取最后一处。
    """
    text = (desc or "").strip()
    if not text:
        return None
    matches = list(_IN_TEXT_LAST_MILE_RE.finditer(text))
    if not matches:
        return None
    m = matches[-1]
    number = (m.group("number") or "").strip().upper().replace(" ", "")
    hint = _prefix_to_hint(m.group("prefix") or "")
    if not number or not hint:
        return None
    if not _is_plausible_last_mile_number(number, hint):
        return None
    return number, hint


def pick_latest_last_mile_from_track_rows(
    rows: list[dict[str, Any]],
) -> tuple[str, LastMileCarrierHint, dict[str, Any]] | None:
    """多条轨迹中取事件时间最新且可识别的一条转单号。"""
    from .db.datetime_util import normalize_tracking_time

    def sort_key(row: dict[str, Any]) -> tuple[str, str, str]:
        event = normalize_tracking_time(str(row.get("tracking_time") or "")) or ""
        created = normalize_tracking_time(str(row.get("created_time") or "")) or ""
        return (event, created, str(row.get("id") or ""))

    for row in sorted(rows, key=sort_key, reverse=True):
        hit = extract_last_mile_from_track_desc(str(row.get("tracking_desc") or ""))
        if hit:
            number, hint = hit
            return number, hint, row
    return None


def infer_last_mile_carrier_hint(number: str) -> LastMileCarrierHint | None:
    """按单号前缀推断承运商（8=FedEx，1Z=UPS，15=DPD，C=CWE，0=DHL）。"""
    tn = (number or "").strip().upper().replace(" ", "")
    if not tn:
        return None
    if tn.startswith("1Z"):
        return "ups"
    if tn.startswith("15"):
        return "dpd"
    if tn.startswith("C"):
        return "conwest"
    if tn.startswith("0"):
        return "dhl"
    if tn.startswith("8"):
        return "fedex"
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
