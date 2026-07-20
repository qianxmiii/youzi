"""工作台首页聚合 overview 测试。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_sla import RISK_SEVERE_OVERDUE, STATUS_OPEN
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from youzi_v2.services.workbench_overview import (
    _merge_todos,
    build_workbench_overview,
)


@pytest.fixture
def database(tmp_path: Path) -> Database:
    return Database(tmp_path / "workbench.db")


def _insert_shipment(
    database: Database,
    *,
    sid: str,
    shipment_no: str,
    status_code: str = "IN_TRANSIT",
    exception_code: str | None = None,
    eta: str | None = None,
    ata: str | None = None,
    delivered_time: str | None = None,
    vessel_voyage: str | None = None,
    destination_port_code: str | None = None,
    payment_status: str = "UNPAID",
) -> None:
    now = now_str()
    with database.lock:
        database.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, status_code, exception_code, eta, ata,
                delivered_time, vessel_voyage, destination_port_code,
                payment_status, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sid,
                shipment_no,
                status_code,
                exception_code,
                eta,
                ata,
                delivered_time,
                vessel_voyage,
                destination_port_code,
                payment_status,
                now,
                now,
            ),
        )
        database.conn.commit()


def test_overview_counts(database: Database) -> None:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    _insert_shipment(database, sid="t1", shipment_no="T-1", status_code="IN_TRANSIT")
    _insert_shipment(
        database,
        sid="t2",
        shipment_no="T-2",
        status_code="IN_TRANSIT",
        exception_code="INSPECTION",
    )
    _insert_shipment(
        database,
        sid="t3",
        shipment_no="T-3",
        status_code="IN_TRANSIT",
        ata=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
    )
    _insert_shipment(
        database,
        sid="t4",
        shipment_no="T-4",
        status_code="DELIVERED",
        delivered_time=f"{monday.isoformat()} 10:00:00",
        payment_status="PAID",
    )
    # 已签收不应计入已到港未签收
    _insert_shipment(
        database,
        sid="t5",
        shipment_no="T-5",
        status_code="DELIVERED",
        ata=f"{monday.isoformat()} 08:00:00",
        delivered_time=f"{monday.isoformat()} 12:00:00",
        payment_status="PAID",
    )

    overview = build_workbench_overview(database)
    assert overview["overview"]["available"] is True
    assert overview["overview"]["inTransit"] == 3  # t1 t2 t3
    assert overview["overview"]["inspection"] == 1
    assert overview["overview"]["arrivedUnsigned"] == 1  # t3
    assert overview["overview"]["deliveredThisWeek"] >= 2


def test_arrivals_aggregate_by_voyage(database: Database) -> None:
    eta = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 15:00:00")
    for i in range(3):
        _insert_shipment(
            database,
            sid=f"a{i}",
            shipment_no=f"A-{i}",
            eta=eta,
            vessel_voyage="OOCL TEST / 001W",
            destination_port_code="GBFXT",
        )
    # 超出窗口
    _insert_shipment(
        database,
        sid="far",
        shipment_no="FAR-1",
        eta=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d 15:00:00"),
        vessel_voyage="OOCL TEST / 001W",
        destination_port_code="GBFXT",
    )

    overview = build_workbench_overview(database, arrival_limit=6)
    assert overview["arrivals"]["available"] is True
    items = overview["arrivals"]["items"]
    assert len(items) == 1
    assert items[0]["shipmentCount"] == 3
    assert items[0]["vesselVoyage"] == "OOCL TEST / 001W"
    assert items[0]["dayGroup"] == "tomorrow"


def test_todos_merge_and_truncate(database: Database) -> None:
    raw = [
        {
            "id": "exc:1",
            "kind": "exception",
            "kindLabel": "严重超时",
            "priority": 1,
            "severity": "severe",
            "shipmentId": "s1",
            "shipmentNo": "SN-1",
            "customer": "C1",
            "title": "严重超时",
            "summary": "严重超时",
            "href": "/shipment-exceptions?status=open",
            "overdueDays": 10,
            "triggerTime": "2026-01-01 00:00:00",
            "updatedTime": "2026-01-02 00:00:00",
        },
        {
            "id": "pay:s1",
            "kind": "payment",
            "kindLabel": "已逾期催款",
            "priority": 2,
            "severity": "high",
            "shipmentId": "s1",
            "shipmentNo": "SN-1",
            "customer": "C1",
            "title": "已逾期催款",
            "summary": "已逾期",
            "href": "/shipments/payment-reminders?scope=todo",
            "overdueDays": 3,
            "triggerTime": "2026-01-03 00:00:00",
            "updatedTime": "2026-01-03 00:00:00",
        },
        {
            "id": "exc:2",
            "kind": "exception",
            "kindLabel": "已超时",
            "priority": 4,
            "severity": "high",
            "shipmentId": "s2",
            "shipmentNo": "SN-2",
            "customer": "C2",
            "title": "已超时",
            "summary": "已超时",
            "href": "/shipment-exceptions?status=open",
            "overdueDays": 1,
            "triggerTime": "2026-01-04 00:00:00",
            "updatedTime": "2026-01-04 00:00:00",
        },
    ]
    merged = _merge_todos(raw, limit=1)
    assert len(merged) == 1
    assert merged[0]["shipmentId"] == "s1"
    assert "2 项待处理" in merged[0]["title"]
    assert set(merged[0]["kinds"]) == {"exception", "payment"}


def test_focus_pending_exceptions_uses_summary(database: Database) -> None:
    _insert_shipment(database, sid="e1", shipment_no="E-1")
    now = now_str()
    with database.lock:
        database.conn.execute(
            """
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                rule_id, rule_scope, channel_code, carrier_code, start_field, start_time,
                due_date, warning_date, event_key, created_time, updated_time
            ) VALUES (
                'al1', 'e1', 'E-1', 'DELIVERY_TIME', ?, ?, 'high',
                '', '', '', '', 'ATD', ?,
                ?, ?, 'ek1', ?, ?
            )
            """,
            (
                RISK_SEVERE_OVERDUE,
                STATUS_OPEN,
                now,
                (date.today() - timedelta(days=3)).isoformat(),
                (date.today() - timedelta(days=6)).isoformat(),
                now,
                now,
            ),
        )
        database.conn.commit()

    overview = build_workbench_overview(database)
    assert overview["focus"]["available"] is True
    assert overview["focus"]["pendingExceptions"] >= 1


def test_module_failure_isolation(database: Database) -> None:
    with patch(
        "youzi_v2.services.workbench_overview._build_overview",
        side_effect=RuntimeError("boom"),
    ):
        overview = build_workbench_overview(database)
    assert overview["overview"]["available"] is False
    assert "boom" in (overview["overview"]["error"] or "")
    assert overview["focus"]["available"] is True
    assert overview["todos"]["available"] is True
    assert overview["arrivals"]["available"] is True
