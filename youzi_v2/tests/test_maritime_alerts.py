"""海运预警聚合测试。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from youzi_v2.db.connection import Database
from youzi_v2.db.port_subscriptions_table import PortSubscriptionsRepository
from youzi_v2.db.vessel_schedules_repository import VesselSchedulesRepository
from youzi_v2.services.maritime_alerts import build_maritime_alerts_overview


@pytest.fixture
def database(tmp_path: Path) -> Database:
    return Database(tmp_path / "maritime_alerts.db")


def _eta_in_days(days: int) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def test_inspection_count_uses_active_exception(database: Database) -> None:
    from youzi_v2.db.datetime_util import now_str
    from youzi_v2.db.shipments_table import TABLE_NAME, ensure_schema

    ensure_schema(database.conn)
    now = now_str()
    with database.lock:
        database.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, status_code, exception_code, created_time, updated_time
            ) VALUES
              ('i1', 'INSP-001', 'IN_TRANSIT', 'INSPECTION', ?, ?),
              ('i2', 'INSP-002', 'IN_TRANSIT', 'INSPECTION', ?, ?),
              ('i3', 'INSP-003', 'INSPECTION', NULL, ?, ?),
              ('h1', 'HOLD-001', 'IN_TRANSIT', 'HOLD', ?, ?)
            """,
            (now, now, now, now, now, now, now, now),
        )
        database.conn.commit()

    overview = build_maritime_alerts_overview(database)
    assert overview["counts"]["inspection"] == 2

    repo = VesselSchedulesRepository(database)
    detail = repo.create(
        {
            "vesselVoyage": "ALERT V001",
            "portCalls": [
                {
                    "portName": "Los Angeles",
                    "sequence": 1,
                    "eta": _eta_in_days(1),
                },
                {
                    "portName": "Oakland",
                    "sequence": 2,
                    "eta": _eta_in_days(2),
                },
            ],
        }
    )
    subscribed_id = detail["portCalls"][1]["id"]
    PortSubscriptionsRepository(database).subscribe(subscribed_id)

    overview = build_maritime_alerts_overview(database)

    assert overview["counts"]["portArrivingSoon"] == 1
    assert overview["counts"]["portDepartingSoon"] == 0
    assert len(overview["urgentPortCalls"]) == 1
    assert overview["urgentPortCalls"][0]["portName"] == "Oakland"
    assert len(overview["etaArrivingSoonPortCalls"]) == 1
    assert overview["voyagesWithAlerts"][0]["arrivingSoonPorts"] == 1


def test_port_alerts_empty_when_no_subscriptions(database: Database) -> None:
    repo = VesselSchedulesRepository(database)
    repo.create(
        {
            "vesselVoyage": "ALERT V002",
            "portCalls": [
                {
                    "portName": "Shanghai",
                    "sequence": 1,
                    "eta": _eta_in_days(1),
                }
            ],
        }
    )

    overview = build_maritime_alerts_overview(database)

    assert overview["counts"]["portArrivingSoon"] == 0
    assert overview["counts"]["portDepartingSoon"] == 0
    assert overview["urgentPortCalls"] == []
    assert overview["etaArrivingSoonPortCalls"] == []
    assert overview["voyagesWithAlerts"] == []
