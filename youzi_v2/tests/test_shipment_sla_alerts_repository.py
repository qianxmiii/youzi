"""运输时效预警列表：异常时长字段。"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_sla import STATUS_OPEN, STATUS_RESOLVED
from youzi_v2.db.shipment_sla_alerts_repository import ShipmentSlaAlertsRepository
from youzi_v2.db.shipment_sla_alerts_table import ensure_schema as ensure_alerts_schema
from youzi_v2.db.shipment_exception_events_table import ensure_schema as ensure_exception_events_schema
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE, ensure_schema as ensure_shipments_schema


def test_list_alerts_includes_exception_duration(tmp_path: Path) -> None:
    db = Database(tmp_path / "sla_exc.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    now = now_str()
    ship_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, atd, exception_code, exception_opened_time,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ship_id, "SN-SLA-EXC", "2026-04-21", "INSPECTION", "2026-06-01 08:00:00", now, now),
        )
        db.conn.execute(
            """
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                due_date, event_key, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                ship_id,
                "SN-SLA-EXC",
                "sla_transit",
                "overdue",
                "open",
                "warning",
                "2026-06-20",
                "k1",
                now,
                now,
            ),
        )
        db.conn.commit()

    repo = ShipmentSlaAlertsRepository(db)
    res = repo.list_alerts(has_exception=True, exception_code="INSPECTION", limit=10)
    assert res["total"] == 1
    item = res["items"][0]
    assert item["exceptionCode"] == "INSPECTION"
    assert item["exceptionDurationLabel"]
    assert item["exceptionDurationSeconds"] is not None
    assert item["totalDaysInTransit"] == item["daysInTransit"]
    assert item["netDaysInTransit"] is not None
    assert item["netDaysInTransit"] <= item["totalDaysInTransit"]

    res_none = repo.list_alerts(has_exception=False, limit=10)
    assert res_none["total"] == 0


def test_list_alerts_includes_resolved_exception_duration(tmp_path: Path) -> None:
    db = Database(tmp_path / "sla_exc_resolved.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    ensure_exception_events_schema(db.conn)
    now = now_str()
    ship_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, atd, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (ship_id, "SN-SLA-PAST", "2026-04-21", now, now),
        )
        db.conn.execute(
            """
            INSERT INTO shipment_exception_events (
                id, shipment_no, exception_code, opened_time, closed_time,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                "SN-SLA-PAST",
                "INSPECTION",
                "2026-06-01 08:00:00",
                "2026-06-10 18:00:00",
                now,
                now,
            ),
        )
        db.conn.execute(
            """
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                due_date, event_key, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                ship_id,
                "SN-SLA-PAST",
                "sla_transit",
                "overdue",
                "open",
                "warning",
                "2026-06-20",
                "k-past",
                now,
                now,
            ),
        )
        db.conn.commit()

    repo = ShipmentSlaAlertsRepository(db)
    fixed_today = date(2026, 7, 10)
    with patch("youzi_v2.db.shipment_sla_alerts_repository.date") as mock_date:
        mock_date.today.return_value = fixed_today
        res = repo.list_alerts(scope="all", limit=10)
    assert res["total"] == 1
    item = res["items"][0]
    assert not item["exceptionCode"]
    assert item["exceptionDurationLabel"] == "9天"
    assert item["exceptionDurationSeconds"] is not None
    assert item["totalDaysInTransit"] == 80
    assert item["netDaysInTransit"] == 71


def test_net_days_in_transit_subtracts_open_exception(tmp_path: Path) -> None:
    db = Database(tmp_path / "sla_net_days.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    now = now_str()
    ship_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, atd, exception_code, exception_opened_time,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ship_id,
                "SN-NET-DAYS",
                "2026-04-21",
                "INSPECTION",
                "2026-06-01 08:00:00",
                now,
                now,
            ),
        )
        db.conn.execute(
            """
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                due_date, event_key, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                ship_id,
                "SN-NET-DAYS",
                "sla_transit",
                "overdue",
                "open",
                "warning",
                "2026-06-20",
                "k-net",
                now,
                now,
            ),
        )
        db.conn.commit()

    repo = ShipmentSlaAlertsRepository(db)
    fixed_today = date(2026, 7, 10)
    with patch("youzi_v2.db.shipment_sla_alerts_repository.date") as mock_date:
        mock_date.today.return_value = fixed_today
        item = repo.list_alerts(has_exception=True, limit=10)["items"][0]
    assert item["totalDaysInTransit"] == 80
    assert item["netDaysInTransit"] == 41
    assert item["daysInTransit"] == item["totalDaysInTransit"]


def _insert_shipment_alert(
    db: Database,
    *,
    ship_id: str,
    alert_id: str,
    shipment_no: str,
    alert_status: str = STATUS_OPEN,
    delivered_time: str = "",
    status_code: str = "",
    atd: str = "2026-04-21",
    alert_type: str = "sla_transit",
) -> None:
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, atd, delivered_time, status_code,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ship_id, shipment_no, atd, delivered_time, status_code, now, now),
        )
        db.conn.execute(
            """
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                due_date, event_key, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                ship_id,
                shipment_no,
                alert_type,
                "overdue",
                alert_status,
                "warning",
                "2026-06-20",
                f"k-{alert_id}",
                now,
                now,
            ),
        )
        db.conn.commit()


def test_list_alerts_todo_excludes_delivered_shipments(tmp_path: Path) -> None:
    db = Database(tmp_path / "sla_todo.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    open_id = str(uuid.uuid4())
    delivered_id = str(uuid.uuid4())
    _insert_shipment_alert(
        db,
        ship_id=open_id,
        alert_id=str(uuid.uuid4()),
        shipment_no="SN-OPEN",
    )
    _insert_shipment_alert(
        db,
        ship_id=delivered_id,
        alert_id=str(uuid.uuid4()),
        shipment_no="SN-DELIVERED",
        delivered_time="2026-06-15 10:00:00",
    )

    repo = ShipmentSlaAlertsRepository(db)
    todo = repo.list_alerts(scope="todo", limit=10)
    assert todo["total"] == 1
    assert todo["items"][0]["shipmentNo"] == "SN-OPEN"

    all_res = repo.list_alerts(scope="all", limit=10)
    assert all_res["total"] == 2


def test_resolve_delivered_stale_alerts(tmp_path: Path) -> None:
    db = Database(tmp_path / "sla_resolve.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    ship_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    _insert_shipment_alert(
        db,
        ship_id=ship_id,
        alert_id=alert_id,
        shipment_no="SN-STALE",
        delivered_time="2026-06-15",
    )

    repo = ShipmentSlaAlertsRepository(db)
    assert repo.resolve_delivered_stale_alerts() == 1
    row = db.conn.execute(
        "SELECT status FROM shipment_sla_alerts WHERE id = ?",
        (alert_id,),
    ).fetchone()
    assert row["status"] == STATUS_RESOLVED


def test_list_alerts_filter_alert_type(tmp_path: Path) -> None:
    db = Database(tmp_path / "sla_alert_type.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    ship_a = str(uuid.uuid4())
    ship_b = str(uuid.uuid4())
    _insert_shipment_alert(
        db,
        ship_id=ship_a,
        alert_id=str(uuid.uuid4()),
        shipment_no="SN-WH",
        alert_type="WAREHOUSE_NO_DEPARTURE",
    )
    _insert_shipment_alert(
        db,
        ship_id=ship_b,
        alert_id=str(uuid.uuid4()),
        shipment_no="SN-PORT",
        alert_type="ARRIVAL_NO_DELIVERY",
    )

    repo = ShipmentSlaAlertsRepository(db)
    wh = repo.list_alerts(scope="all", alert_type="WAREHOUSE_NO_DEPARTURE", limit=10)
    assert len(wh["items"]) == 1
    assert wh["items"][0]["alertType"] == "WAREHOUSE_NO_DEPARTURE"

    port = repo.list_alerts(scope="all", alert_type="ARRIVAL_NO_DELIVERY", limit=10)
    assert len(port["items"]) == 1
    assert port["items"][0]["alertType"] == "ARRIVAL_NO_DELIVERY"


def test_list_alerts_days_in_transit_uses_delivered_date(tmp_path: Path) -> None:
    db = Database(tmp_path / "sla_days.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    ship_id = str(uuid.uuid4())
    _insert_shipment_alert(
        db,
        ship_id=ship_id,
        alert_id=str(uuid.uuid4()),
        shipment_no="SN-DAYS",
        delivered_time="2026-06-15",
        atd="2026-04-21",
    )

    repo = ShipmentSlaAlertsRepository(db)
    res = repo.list_alerts(scope="all", limit=10)
    assert res["items"][0]["daysInTransit"] == 55


def test_list_alerts_channel_estimated_days_fallback(tmp_path: Path) -> None:
    """系统卡点预警无 rule_id 时，仍展示渠道配置的预估天数。"""
    from youzi_v2.db.channel_sla_rules_table import ensure_schema as ensure_channel_sla_schema

    db = Database(tmp_path / "sla_channel_est.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    ensure_channel_sla_schema(db.conn)
    now = now_str()
    ship_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    rule_id = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            """
            INSERT INTO channel_sla_rules (
                id, channel_code, carrier_code, start_field, estimated_days,
                warning_days, severe_overdue_days, enabled, note, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rule_id, "STS-LAX", "", "ATD", 45, 3, 7, 1, "", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, channel_code, carrier_code, ata,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ship_id, "SN-CHANNEL-SLA", "STS-LAX", "CAR1", "2026-06-13", now, now),
        )
        db.conn.execute(
            """
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                due_date, event_key, channel_code, carrier_code, rule_scope,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                ship_id,
                "SN-CHANNEL-SLA",
                "ARRIVAL_NO_DELIVERY",
                "overdue",
                "open",
                "warning",
                "2026-06-23",
                f"k-{alert_id}",
                "STS-LAX",
                "CAR1",
                "system",
                now,
                now,
            ),
        )
        db.conn.commit()

    repo = ShipmentSlaAlertsRepository(db)
    res = repo.list_alerts(scope="all", limit=10)
    assert res["total"] == 1
    assert res["items"][0]["estimatedDays"] == 45


def test_follow_up_creates_record_and_sets_acknowledged(tmp_path: Path) -> None:
    from youzi_v2.db.shipment_sla_alert_followups_table import ensure_schema as ensure_followups_schema

    db = Database(tmp_path / "sla_follow.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    ensure_followups_schema(db.conn)
    now = now_str()
    ship_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (id, shipment_no, created_time, updated_time)
            VALUES (?, ?, ?, ?)
            """,
            (ship_id, "SN-FOLLOW", now, now),
        )
        db.conn.execute(
            """
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                due_date, event_key, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                ship_id,
                "SN-FOLLOW",
                "DELIVERY_TIME",
                "overdue",
                "open",
                "warning",
                "2026-06-20",
                "k-follow",
                now,
                now,
            ),
        )
        db.conn.commit()

    repo = ShipmentSlaAlertsRepository(db)
    assert repo.follow_up(alert_id) is True
    assert repo.follow_up(alert_id) is True
    res = repo.list_alerts(scope="all", limit=10)
    item = res["items"][0]
    assert item["status"] == "acknowledged"
    assert item["followUpCount"] == 2
    assert item["lastFollowUpTime"]


def test_resolve_alert_from_followed(tmp_path: Path) -> None:
    from youzi_v2.db.shipment_sla_alert_followups_table import ensure_schema as ensure_followups_schema

    db = Database(tmp_path / "sla_resolve_manual.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    ensure_followups_schema(db.conn)
    now = now_str()
    ship_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (id, shipment_no, created_time, updated_time)
            VALUES (?, ?, ?, ?)
            """,
            (ship_id, "SN-RES", now, now),
        )
        db.conn.execute(
            """
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                due_date, event_key, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                ship_id,
                "SN-RES",
                "DELIVERY_TIME",
                "overdue",
                "open",
                "warning",
                "2026-06-20",
                "k-res",
                now,
                now,
            ),
        )
        db.conn.commit()

    repo = ShipmentSlaAlertsRepository(db)
    assert repo.follow_up(alert_id) is True
    assert repo.resolve_alert(alert_id) is True
    row = db.conn.execute(
        "SELECT status FROM shipment_sla_alerts WHERE id = ?",
        (alert_id,),
    ).fetchone()
    assert row["status"] == STATUS_RESOLVED
