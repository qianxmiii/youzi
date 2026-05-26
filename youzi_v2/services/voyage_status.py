"""航次挂靠与运单海运状态计算。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from youzi_v2.db.datetime_util import normalize_tracking_time

_STATUS_LABELS: dict[str, str] = {
    "departed": "已离港",
    "arrived": "已到港",
    "arriving_soon": "三天内到港",
    "departing_soon": "三天内离港",
    "in_transit": "在途",
    "planned": "计划中",
    "unknown": "待更新",
}


def status_label(code: str) -> str:
    return _STATUS_LABELS.get(code, code)


def _parse_dt(raw: str | None) -> datetime | None:
    text = normalize_tracking_time(raw)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19] if fmt != "%Y-%m-%d" else text[:10], fmt)
        except ValueError:
            continue
    return None


def _within_days(target: datetime | None, *, days: int, now: datetime) -> bool:
    if target is None:
        return False
    end = now + timedelta(days=days)
    return now <= target <= end


def port_call_status(
    *,
    eta: str | None,
    ata: str | None,
    etd: str | None,
    atd: str | None,
    now: datetime | None = None,
) -> str:
    """挂靠节点状态（单值 code）。"""
    now = now or datetime.now()
    if ata and not atd:
        return "arrived"
    if atd:
        return "departed"
    eta_dt = _parse_dt(eta)
    if eta and not ata and _within_days(eta_dt, days=3, now=now):
        return "arriving_soon"
    etd_dt = _parse_dt(etd)
    if etd and not atd and _within_days(etd_dt, days=3, now=now):
        return "departing_soon"
    if eta or etd:
        return "planned"
    return "unknown"


def enrich_port_call(row: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    code = port_call_status(
        eta=row.get("eta"),
        ata=row.get("ata"),
        etd=row.get("etd"),
        atd=row.get("atd"),
        now=now,
    )
    return {**row, "status": code, "statusLabel": status_label(code)}


def shipment_maritime_status(
    *,
    eta: str | None,
    ata: str | None,
    etd: str | None,
    atd: str | None,
    now: datetime | None = None,
) -> str:
    now = now or datetime.now()
    if ata:
        return "arrived"
    if atd:
        return "in_transit"
    eta_dt = _parse_dt(eta)
    if eta and _within_days(eta_dt, days=3, now=now):
        return "arriving_soon"
    etd_dt = _parse_dt(etd)
    if etd and not atd and _within_days(etd_dt, days=3, now=now):
        return "departing_soon"
    if eta or etd or atd:
        return "planned"
    return "unknown"


def enrich_shipment(row: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    code = shipment_maritime_status(
        eta=row.get("eta"),
        ata=row.get("ata"),
        etd=row.get("etd"),
        atd=row.get("atd"),
        now=now,
    )
    return {**row, "maritimeStatus": code, "maritimeStatusLabel": status_label(code)}


def summarize_shipment_statuses(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "arrivingSoon": 0,
        "departingSoon": 0,
        "arrived": 0,
        "inTransit": 0,
        "planned": 0,
        "unknown": 0,
    }
    key_map = {
        "arriving_soon": "arrivingSoon",
        "departing_soon": "departingSoon",
        "arrived": "arrived",
        "in_transit": "inTransit",
        "planned": "planned",
        "unknown": "unknown",
    }
    for item in items:
        code = item.get("maritimeStatus") or shipment_maritime_status(
            eta=item.get("eta"),
            ata=item.get("ata"),
            etd=item.get("etd"),
            atd=item.get("atd"),
        )
        bucket = key_map.get(code, "unknown")
        counts[bucket] += 1
    return counts
