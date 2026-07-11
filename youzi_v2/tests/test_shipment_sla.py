"""运输时效预警计算单测。"""
from __future__ import annotations

from datetime import date

from youzi_v2.db.shipment_sla import (
    ALERT_ARRIVAL_NO_DELIVERY,
    ALERT_WAREHOUSE_NO_DEPARTURE,
    ARRIVAL_NO_DELIVERY_DAYS,
    WAREHOUSE_NO_DEPARTURE_DAYS,
    compute_arrival_no_delivery_context,
    compute_days_in_transit,
    compute_due_context,
    compute_risk_level,
    compute_warehouse_no_departure_context,
    days_since_start,
    has_departure_schedule,
    is_delivered,
    match_channel_rule,
    build_event_key,
)


def test_due_date_ignores_expected_delivery_time_and_uses_atd() -> None:
    row = {"expected_delivery_time": "2026-07-02", "atd": "2026-06-01"}
    rule = {
        "id": "r1",
        "estimatedDays": 35,
        "warningDays": 3,
        "severeOverdueDays": 7,
        "startField": "ATD",
        "enabled": True,
        "carrierCode": "",
    }
    ctx = compute_due_context(row, rule)
    assert ctx is not None
    assert ctx["dueDate"] == "2026-07-06"
    assert ctx["ruleScope"] == "channel"
    assert ctx["startField"] == "ATD"


def test_due_date_from_atd_when_no_expected_delivery() -> None:
    row = {"expected_delivery_time": "", "atd": "2026-06-01 10:00:00"}
    rule = {
        "id": "r1",
        "estimatedDays": 35,
        "warningDays": 3,
        "severeOverdueDays": 7,
        "startField": "ATD",
        "enabled": True,
        "carrierCode": "",
    }
    ctx = compute_due_context(row, rule)
    assert ctx is not None
    assert ctx["dueDate"] == "2026-07-06"
    assert ctx["ruleScope"] == "channel"


def test_risk_level_progression() -> None:
    due = date(2026, 7, 6)
    assert compute_risk_level(today=date(2026, 7, 3), due_day=due, warning_days=3, severe_overdue_days=7) == "warning_soon"
    assert compute_risk_level(today=date(2026, 7, 7), due_day=due, warning_days=3, severe_overdue_days=7) == "overdue"
    assert compute_risk_level(today=date(2026, 7, 14), due_day=due, warning_days=3, severe_overdue_days=7) == "severe_overdue"
    assert compute_risk_level(today=date(2026, 7, 1), due_day=due, warning_days=3, severe_overdue_days=7) is None


def test_days_since_start() -> None:
    assert days_since_start("2026-06-01", today=date(2026, 6, 1)) == 0
    assert days_since_start("2026-06-01 10:00:00", today=date(2026, 6, 10)) == 9
    assert days_since_start("") is None


def test_compute_days_in_transit_uses_today_when_not_delivered() -> None:
    assert compute_days_in_transit("2026-04-21", today=date(2026, 7, 7)) == 77


def test_compute_days_in_transit_uses_delivered_date() -> None:
    assert compute_days_in_transit(
        "2026-04-21",
        delivered_time="2026-06-15",
    ) == 55


def test_is_delivered_with_time_or_status() -> None:
    assert is_delivered({"delivered_time": "2026-06-01", "status_code": "IN_TRANSIT"})
    assert is_delivered({"delivered_time": "", "status_code": "DELIVERED"})
    assert not is_delivered({"delivered_time": "", "status_code": "IN_TRANSIT"})


def test_match_carrier_specific_rule() -> None:
    rules = {
        "CH1": [
            {"channelCode": "CH1", "carrierCode": "COSCO", "estimatedDays": 33, "enabled": True},
            {"channelCode": "CH1", "carrierCode": "", "estimatedDays": 35, "enabled": True},
        ]
    }
    matched = match_channel_rule(rules, channel_code="CH1", carrier_code="COSCO")
    assert matched is not None
    assert matched["estimatedDays"] == 33


def test_warehouse_no_departure_after_seven_days() -> None:
    row = {"warehouse_entry_time": "2026-06-01", "etd": "", "atd": ""}
    ctx = compute_warehouse_no_departure_context(row, today=date(2026, 6, 8))
    assert ctx is not None
    assert ctx["alertType"] == ALERT_WAREHOUSE_NO_DEPARTURE
    assert ctx["dueDate"] == "2026-06-08"
    assert ctx["riskLevel"] == "overdue"


def test_warehouse_no_departure_skips_when_etd_exists() -> None:
    row = {"warehouse_entry_time": "2026-06-01", "etd": "2026-06-10", "atd": ""}
    assert has_departure_schedule(row)
    assert compute_warehouse_no_departure_context(row, today=date(2026, 6, 20)) is None


def test_arrival_no_delivery_after_twelve_days() -> None:
    row = {"ata": "2026-06-01"}
    ctx = compute_arrival_no_delivery_context(row, today=date(2026, 6, 13))
    assert ctx is not None
    assert ctx["alertType"] == ALERT_ARRIVAL_NO_DELIVERY
    assert ctx["dueDate"] == "2026-06-13"


def test_stage_event_keys() -> None:
    assert build_event_key(
        shipment_id="s1",
        alert_type=ALERT_WAREHOUSE_NO_DEPARTURE,
        anchor_date="2026-06-01",
    ) == "s1|WAREHOUSE_NO_DEPARTURE|2026-06-01"
    assert build_event_key(
        shipment_id="s1",
        rule_id="r1",
        due_date="2026-07-06",
    ) == "s1|DELIVERY_TIME|r1|2026-07-06"
