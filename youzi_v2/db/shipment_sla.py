"""运输时效预警：截止日与风险等级计算。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from .datetime_util import DATETIME_FMT

RISK_WARNING_SOON = "warning_soon"
RISK_OVERDUE = "overdue"
RISK_SEVERE_OVERDUE = "severe_overdue"

ALERT_DELIVERY_TIME = "DELIVERY_TIME"
ALERT_WAREHOUSE_NO_DEPARTURE = "WAREHOUSE_NO_DEPARTURE"
ALERT_ARRIVAL_NO_DELIVERY = "ARRIVAL_NO_DELIVERY"

WAREHOUSE_NO_DEPARTURE_DAYS = 7
ARRIVAL_NO_DELIVERY_DAYS = 10

STATUS_OPEN = "open"
STATUS_ACKNOWLEDGED = "acknowledged"
STATUS_CONVERTED = "converted"
STATUS_RESOLVED = "resolved"
STATUS_IGNORED = "ignored"

ACTIVE_STATUSES = frozenset({STATUS_OPEN, STATUS_ACKNOWLEDGED})
TERMINAL_STATUSES = frozenset({STATUS_CONVERTED, STATUS_IGNORED, STATUS_RESOLVED})

DEFAULT_WARNING_DAYS = 3
DEFAULT_SEVERE_OVERDUE_DAYS = 7


def parse_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in (DATETIME_FMT, "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    if len(raw) >= 10:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def is_delivered(row: dict[str, Any]) -> bool:
    status = (row.get("status_code") or "").strip().upper()
    delivered = (row.get("delivered_time") or "").strip()
    return status == "DELIVERED" or bool(delivered)


def match_channel_rule(
    rules_by_channel: dict[str, list[dict[str, Any]]],
    *,
    channel_code: str,
    carrier_code: str | None,
) -> dict[str, Any] | None:
    channel = (channel_code or "").strip()
    if not channel:
        return None
    rules = rules_by_channel.get(channel) or []
    if not rules:
        return None
    carrier = (carrier_code or "").strip()
    enabled = [r for r in rules if r.get("enabled")]
    if not enabled:
        return None
    if carrier:
        for rule in enabled:
            if (rule.get("carrierCode") or "").strip() == carrier:
                return rule
    for rule in enabled:
        if not (rule.get("carrierCode") or "").strip():
            return rule
    return None


def has_departure_schedule(row: dict[str, Any]) -> bool:
    return bool((row.get("etd") or "").strip()) or bool((row.get("atd") or "").strip())


def compute_warehouse_no_departure_context(
    row: dict[str, Any],
    *,
    today: date | None = None,
) -> dict[str, Any] | None:
    """入库后 7 天仍无 ETD/ATD 时生成入库未开船预警。"""
    entry_raw = (row.get("warehouse_entry_time") or "").strip()
    entry_day = parse_date(entry_raw)
    if not entry_day or has_departure_schedule(row):
        return None
    check_day = today or date.today()
    due_day = entry_day + timedelta(days=WAREHOUSE_NO_DEPARTURE_DAYS)
    if check_day < due_day:
        return None
    due_iso = due_day.isoformat()
    return {
        "alertType": ALERT_WAREHOUSE_NO_DEPARTURE,
        "dueDate": due_iso,
        "warningDate": due_iso,
        "startField": "warehouse_entry_time",
        "startTime": entry_raw[:10] if len(entry_raw) >= 10 else entry_raw,
        "ruleScope": "system",
        "ruleId": "",
        "riskLevel": RISK_OVERDUE,
    }


def compute_arrival_no_delivery_context(
    row: dict[str, Any],
    *,
    today: date | None = None,
) -> dict[str, Any] | None:
    """ATA 后 10 天仍未签收时生成到港未送仓预警。"""
    ata_raw = (row.get("ata") or "").strip()
    ata_day = parse_date(ata_raw)
    if not ata_day:
        return None
    check_day = today or date.today()
    due_day = ata_day + timedelta(days=ARRIVAL_NO_DELIVERY_DAYS)
    if check_day < due_day:
        return None
    due_iso = due_day.isoformat()
    return {
        "alertType": ALERT_ARRIVAL_NO_DELIVERY,
        "dueDate": due_iso,
        "warningDate": due_iso,
        "startField": "ATA",
        "startTime": ata_raw[:10] if len(ata_raw) >= 10 else ata_raw,
        "ruleScope": "system",
        "ruleId": "",
        "riskLevel": RISK_OVERDUE,
    }


def compute_due_context(
    row: dict[str, Any],
    rule: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """返回 due_date、warning_date、起算信息；无法计算时返回 None。"""
    warning_days = int(rule.get("warningDays") or DEFAULT_WARNING_DAYS) if rule else DEFAULT_WARNING_DAYS
    severe_days = (
        int(rule.get("severeOverdueDays") or DEFAULT_SEVERE_OVERDUE_DAYS)
        if rule
        else DEFAULT_SEVERE_OVERDUE_DAYS
    )

    if not rule:
        return None

    start_field = (rule.get("startField") or "ATD").strip().upper()
    if start_field != "ATD":
        return None

    atd_raw = (row.get("atd") or "").strip()
    atd_day = parse_date(atd_raw)
    if not atd_day:
        return None

    estimated = int(rule.get("estimatedDays") or 0)
    if estimated <= 0:
        return None

    due_day = atd_day + timedelta(days=estimated)
    warning_day = due_day - timedelta(days=warning_days)
    return {
        "dueDate": due_day.isoformat(),
        "warningDate": warning_day.isoformat(),
        "startField": start_field,
        "startTime": atd_raw[:10] if len(atd_raw) >= 10 else atd_raw,
        "ruleScope": "channel",
        "ruleId": rule.get("id") or "",
        "warningDays": warning_days,
        "severeOverdueDays": severe_days,
        "alertType": ALERT_DELIVERY_TIME,
    }


def compute_risk_level(
    *,
    today: date,
    due_day: date,
    warning_days: int,
    severe_overdue_days: int,
) -> str | None:
    warning_start = due_day - timedelta(days=max(0, warning_days))
    if today < warning_start:
        return None
    severe_cutoff = due_day + timedelta(days=max(0, severe_overdue_days))
    if today > severe_cutoff:
        return RISK_SEVERE_OVERDUE
    if today > due_day:
        return RISK_OVERDUE
    return RISK_WARNING_SOON


def risk_to_severity(risk_level: str) -> str:
    if risk_level == RISK_SEVERE_OVERDUE:
        return "urgent"
    if risk_level == RISK_OVERDUE:
        return "warning"
    return "info"


def days_until_due(today: date, due_day: date) -> int:
    return (due_day - today).days


def days_since_start(start_time: str | None, *, today: date | None = None) -> int | None:
    """起算日至今天的自然日数（含当天为 0）。"""
    start_day = parse_date(start_time)
    if not start_day:
        return None
    end = today or date.today()
    return max(0, (end - start_day).days)


def compute_days_in_transit(
    start_time: str | None,
    *,
    delivered_time: str | None = None,
    today: date | None = None,
) -> int | None:
    """已运输天数：未签收用今天 − 起算日；已签收用签收日 − 起算日。"""
    start_day = parse_date(start_time)
    if not start_day:
        return None
    delivered_day = parse_date(delivered_time)
    if delivered_day is not None:
        return max(0, (delivered_day - start_day).days)
    return days_since_start(start_time, today=today)


def build_event_key(
    *,
    shipment_id: str,
    alert_type: str = ALERT_DELIVERY_TIME,
    rule_id: str = "",
    due_date: str = "",
    anchor_date: str = "",
) -> str:
    sid = shipment_id.strip()
    at = (alert_type or ALERT_DELIVERY_TIME).strip()
    if at == ALERT_DELIVERY_TIME:
        return f"{sid}|{at}|{(rule_id or '').strip()}|{due_date.strip()}"
    anchor = (anchor_date or due_date).strip()
    return f"{sid}|{at}|{anchor}"
