"""船名 / 航次 / 船名航次 组合与解析。"""

from __future__ import annotations


def parse_vessel_voyage(combined: str | None) -> tuple[str | None, str | None]:
    """从「船名/航次」拆分为 (船名, 航次)。"""
    text = (combined or "").strip()
    if not text:
        return None, None
    if "/" not in text:
        return text, None
    idx = text.rfind("/")
    name = text[:idx].strip()
    voyage = text[idx + 1 :].strip()
    return (name or None), (voyage or None)


def compose_vessel_voyage(
    vessel_name: str | None,
    voyage_no: str | None,
    *,
    fallback: str | None = None,
) -> str:
    name = (vessel_name or "").strip()
    voyage = (voyage_no or "").strip()
    if name and voyage:
        return f"{name}/{voyage}"
    if name:
        return name
    if voyage:
        return voyage
    return (fallback or "").strip()


def resolve_voyage_identity(
    *,
    vessel_voyage: str | None = None,
    vessel_name: str | None = None,
    voyage_no: str | None = None,
) -> tuple[str, str | None, str | None]:
    """
    归一化航次标识，返回 (vessel_voyage, vessel_name, voyage_no)。
    优先用显式船名+航次组合；否则解析/保留船名航次。
    """
    name = (vessel_name or "").strip() or None
    voyage = (voyage_no or "").strip() or None
    combined = (vessel_voyage or "").strip()

    if name or voyage:
        vv = compose_vessel_voyage(name, voyage, fallback=combined)
        if not vv:
            raise ValueError("船名或航次至少填写一项")
        if not name and combined:
            name, _ = parse_vessel_voyage(combined)
        if not voyage and combined:
            _, voyage = parse_vessel_voyage(combined)
        return vv, name, voyage

    if not combined:
        raise ValueError("请填写船名航次，或分别填写船名与航次")
    parsed_name, parsed_voyage = parse_vessel_voyage(combined)
    return combined, parsed_name, parsed_voyage


def shipment_voyage_match_sql(
    vessel_voyage: str,
    vessel_name: str | None = None,
    voyage_no: str | None = None,
    *,
    table_alias: str = "",
) -> tuple[str, list[str]]:
    """
    运单与航次关联条件（OR）。
    兼容：运单只填船名、航次主数据为「船名/航次」组合等情况。
    返回 (SQL 片段, 参数)，片段形如 (a OR b OR ...)。
    """
    vv = (vessel_voyage or "").strip()
    name = (vessel_name or "").strip()
    voy = (voyage_no or "").strip()
    if not name and vv:
        parsed_name, parsed_voy = parse_vessel_voyage(vv)
        name = (parsed_name or "").strip()
        if not voy:
            voy = (parsed_voy or "").strip()

    col = f"{table_alias}." if table_alias else ""

    tokens: list[str] = []
    for raw in (vv, name, compose_vessel_voyage(name, voy) if name and voy else None):
        t = (raw or "").strip()
        if t and t not in tokens:
            tokens.append(t)

    parts: list[str] = []
    params: list[str] = []
    for token in tokens:
        parts.append(f"{col}vessel_voyage = ? COLLATE NOCASE")
        params.append(token)
    if name:
        parts.append(f"{col}vessel_name = ? COLLATE NOCASE")
        params.append(name)
    if name and voy:
        parts.append(
            f"({col}vessel_name = ? COLLATE NOCASE AND {col}voyage_no = ? COLLATE NOCASE)"
        )
        params.extend([name, voy])

    if not parts:
        return "1=0", []
    return f"({' OR '.join(parts)})", params
