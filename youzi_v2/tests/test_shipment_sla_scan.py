"""运输时效扫描：阶段卡点预警。"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch

from youzi_v2.db.channel_sla_rules_repository import ChannelSlaRulesRepository
from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_sla import ALERT_WAREHOUSE_NO_DEPARTURE
from youzi_v2.db.shipment_sla_alerts_repository import ShipmentSlaAlertsRepository
from youzi_v2.db.shipment_sla_alerts_table import ensure_schema as ensure_alerts_schema
from youzi_v2.db.shipment_exception_followup_repository import (
    ShipmentExceptionFollowupRepository,
)
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE, ensure_schema as ensure_shipments_schema
from youzi_v2.services.shipment_sla_scan import scan_shipment_sla_alerts


def _insert_shipment(
    db: Database,
    *,
    ship_id: str,
    shipment_no: str,
    warehouse_entry_time: str = "",
    etd: str = "",
    atd: str = "",
    ata: str = "",
    channel_code: str = "CH1",
) -> None:
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, channel_code, warehouse_entry_time, etd, atd, ata,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ship_id,
                shipment_no,
                channel_code,
                warehouse_entry_time,
                etd,
                atd,
                ata,
                now,
                now,
            ),
        )
        db.conn.commit()


def test_scan_creates_warehouse_no_departure_alert(tmp_path: Path) -> None:
    db = Database(tmp_path / "sla_scan.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    ship_id = str(uuid.uuid4())
    _insert_shipment(
        db,
        ship_id=ship_id,
        shipment_no="SN-WH-1",
        warehouse_entry_time="2026-06-01",
    )

    alerts_repo = ShipmentSlaAlertsRepository(db)
    rules_repo = ChannelSlaRulesRepository(db)
    followup_repo = ShipmentExceptionFollowupRepository(db)

    with patch("youzi_v2.services.shipment_sla_scan.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 10)
        result = scan_shipment_sla_alerts(
            alerts_repo,
            rules_repo,
            followup_repo,
            force=True,
            trigger="manual",
        )

    assert result["created"] == 1
    rows = alerts_repo.list_alerts(scope="todo", limit=10)
    assert rows["total"] == 1
    item = rows["items"][0]
    assert item["alertType"] == ALERT_WAREHOUSE_NO_DEPARTURE
    assert item["shipmentNo"] == "SN-WH-1"


def test_scan_closes_warehouse_alert_when_atd_filled(tmp_path: Path) -> None:
    db = Database(tmp_path / "sla_scan2.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    ship_id = str(uuid.uuid4())
    alert_id = str(uuid.uuid4())
    now = now_str()
    _insert_shipment(
        db,
        ship_id=ship_id,
        shipment_no="SN-WH-2",
        warehouse_entry_time="2026-06-01",
        atd="2026-06-15",
    )
    with db.lock:
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
                "SN-WH-2",
                ALERT_WAREHOUSE_NO_DEPARTURE,
                "overdue",
                "open",
                "warning",
                "2026-06-08",
                f"{ship_id}|WAREHOUSE_NO_DEPARTURE|2026-06-01",
                now,
                now,
            ),
        )
        db.conn.commit()

    alerts_repo = ShipmentSlaAlertsRepository(db)
    rules_repo = ChannelSlaRulesRepository(db)
    followup_repo = ShipmentExceptionFollowupRepository(db)

    with patch("youzi_v2.services.shipment_sla_scan.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 20)
        result = scan_shipment_sla_alerts(
            alerts_repo,
            rules_repo,
            followup_repo,
            force=True,
            trigger="manual",
        )

    assert result["resolved"] >= 1
    row = db.conn.execute(
        "SELECT status FROM shipment_sla_alerts WHERE id = ?",
        (alert_id,),
    ).fetchone()
    assert row["status"] == "resolved"
