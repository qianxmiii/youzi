"""运输时效预警计算单测。"""
from __future__ import annotations

from datetime import date

from youzi_v2.db.shipment_sla import (
    ALERT_ARRIVAL_NO_DELIVERY,
    ALERT_DEST_WAREHOUSE_NO_DISPATCH,
    ALERT_WAREHOUSE_NO_DEPARTURE,
    SLA_FIELD_ARRIVED_POD_TIME,
    SLA_FIELD_DEST_TRANSIT_TIME,
    SLA_FIELD_WAREHOUSE_IN_TIME,
    compute_arrival_no_delivery_context,
    compute_days_in_transit,
    compute_dest_warehouse_no_dispatch_context,
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


def test_no_rule_returns_none() -> None:
    assert compute_due_context({"atd": "2026-06-01"}, None) is None


def test_risk_levels() -> None:
    due = date(2026, 7, 6)
    assert compute_risk_level(
        today=date(2026, 7, 2),
        due_day=due,
        warning_days=3,
        severe_overdue_days=7,
    ) is None
    assert (
        compute_risk_level(
            today=date(2026, 7, 3),
            due_day=due,
            warning_days=3,
            severe_overdue_days=7,
        )
        == "warning_soon"
    )
    assert (
        compute_risk_level(
            today=date(2026, 7, 7),
            due_day=due,
            warning_days=3,
            severe_overdue_days=7,
        )
        == "overdue"
    )
    assert (
        compute_risk_level(
            today=date(2026, 7, 14),
            due_day=due,
            warning_days=3,
            severe_overdue_days=7,
        )
        == "severe_overdue"
    )


def test_days_since_start() -> None:
    assert days_since_start("2026-06-01", today=date(2026, 6, 1)) == 0
    assert days_since_start("2026-06-01", today=date(2026, 6, 8)) == 7
    assert days_since_start("") is None


def test_compute_days_in_transit_uses_today_when_not_delivered() -> None:
    assert compute_days_in_transit("2026-04-21", today=date(2026, 7, 7)) == 77


def test_compute_days_in_transit_uses_delivered_date() -> None:
    assert compute_days_in_transit(
        "2026-04-21",
        delivered_time="2026-06-15",
    ) == 55


def test_is_delivered_uses_route_status() -> None:
    assert is_delivered({"route_status": "TRACK_SIGNED"})
    assert is_delivered({"routeStatus": "TRACK_SIGNED"})
    assert not is_delivered({"route_status": "LAST_MILE_HANDOVER"})
    assert not is_delivered({"route_status": "ARRIVED_POD"})
    assert not is_delivered({"delivered_time": "2026-06-01", "status_code": "DELIVERED"})
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


def test_warehouse_no_departure_uses_route_warehouse_in_time() -> None:
    row = {SLA_FIELD_WAREHOUSE_IN_TIME: "2026-06-01", "etd": "", "atd": ""}
    assert compute_warehouse_no_departure_context(row, today=date(2026, 6, 8)) is None
    ctx = compute_warehouse_no_departure_context(row, today=date(2026, 6, 9))
    assert ctx is not None
    assert ctx["alertType"] == ALERT_WAREHOUSE_NO_DEPARTURE
    assert ctx["dueDate"] == "2026-06-08"
    assert ctx["startField"] == SLA_FIELD_WAREHOUSE_IN_TIME
    assert ctx["riskLevel"] == "overdue"
    # 旧 warehouse_entry_time 不再作为起算
    assert (
        compute_warehouse_no_departure_context(
            {"warehouse_entry_time": "2026-06-01", "etd": "", "atd": ""},
            today=date(2026, 6, 20),
        )
        is None
    )


def test_warehouse_no_departure_skips_when_etd_exists() -> None:
    row = {SLA_FIELD_WAREHOUSE_IN_TIME: "2026-06-01", "etd": "2026-06-10", "atd": ""}
    assert has_departure_schedule(row)
    assert compute_warehouse_no_departure_context(row, today=date(2026, 6, 20)) is None


def test_arrival_no_delivery_uses_route_arrived_pod_time() -> None:
    row = {SLA_FIELD_ARRIVED_POD_TIME: "2026-06-01"}
    assert compute_arrival_no_delivery_context(row, today=date(2026, 6, 6)) is None
    ctx = compute_arrival_no_delivery_context(row, today=date(2026, 6, 7))
    assert ctx is not None
    assert ctx["alertType"] == ALERT_ARRIVAL_NO_DELIVERY
    assert ctx["dueDate"] == "2026-06-06"
    assert ctx["startField"] == SLA_FIELD_ARRIVED_POD_TIME
    # 旧 ATA 不再作为起算
    assert (
        compute_arrival_no_delivery_context(
            {"ata": "2026-06-01"},
            today=date(2026, 6, 20),
        )
        is None
    )


def test_arrival_no_delivery_skips_when_route_fulfilled() -> None:
    pod = {SLA_FIELD_ARRIVED_POD_TIME: "2026-06-01"}
    assert (
        compute_arrival_no_delivery_context(
            {**pod, "route_status": "DEST_TRANSIT_WAREHOUSE"},
            today=date(2026, 6, 20),
        )
        is None
    )
    assert (
        compute_arrival_no_delivery_context(
            {**pod, SLA_FIELD_DEST_TRANSIT_TIME: "2026-06-03"},
            today=date(2026, 6, 20),
        )
        is None
    )
    assert (
        compute_arrival_no_delivery_context(
            {**pod, "route_status": "TRACK_SIGNED"},
            today=date(2026, 6, 20),
        )
        is None
    )


def test_dest_warehouse_no_dispatch_uses_route_dest_transit_time() -> None:
    row = {SLA_FIELD_DEST_TRANSIT_TIME: "2026-06-01"}
    assert compute_dest_warehouse_no_dispatch_context(row, today=date(2026, 6, 6)) is None
    ctx = compute_dest_warehouse_no_dispatch_context(row, today=date(2026, 6, 7))
    assert ctx is not None
    assert ctx["alertType"] == ALERT_DEST_WAREHOUSE_NO_DISPATCH
    assert ctx["dueDate"] == "2026-06-06"
    assert ctx["startField"] == SLA_FIELD_DEST_TRANSIT_TIME


def test_dest_warehouse_no_dispatch_skips_when_dispatched() -> None:
    base = {SLA_FIELD_DEST_TRANSIT_TIME: "2026-06-01"}
    assert (
        compute_dest_warehouse_no_dispatch_context(
            {**base, "route_status": "LAST_MILE_HANDOVER"},
            today=date(2026, 6, 20),
        )
        is None
    )
    assert (
        compute_dest_warehouse_no_dispatch_context(
            {**base, "route_status": "TRACK_SIGNED"},
            today=date(2026, 6, 20),
        )
        is None
    )


def test_stage_event_keys() -> None:
    assert build_event_key(
        shipment_no="SN1",
        alert_type=ALERT_WAREHOUSE_NO_DEPARTURE,
        anchor_date="2026-06-01",
    ) == "SN1|WAREHOUSE_NO_DEPARTURE|2026-06-01"
    assert build_event_key(
        shipment_no="SN1",
        rule_id="r1",
        due_date="2026-07-06",
    ) == "SN1|DELIVERY_TIME|r1|2026-07-06"
    assert build_event_key(
        shipment_id="s1",
        alert_type=ALERT_WAREHOUSE_NO_DEPARTURE,
        anchor_date="2026-06-01",
    ) == "s1|WAREHOUSE_NO_DEPARTURE|2026-06-01"
    assert build_event_key(
        shipment_no="SN1",
        alert_type=ALERT_DEST_WAREHOUSE_NO_DISPATCH,
        anchor_date="2026-06-01",
    ) == "SN1|DEST_WAREHOUSE_NO_DISPATCH|2026-06-01"
