"""运输时效统计。"""

from __future__ import annotations

from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_groups_table import ensure_schema as ensure_group_schema
from youzi_v2.db.shipment_performance_statistics_repository import (
    ShipmentPerformanceStatisticsRepository,
)
from youzi_v2.db.shipments_table import TABLE_NAME, ensure_schema as ensure_shipments_schema
from youzi_v2.schemas.shipment_performance_statistics import ShipmentPerformanceQuery


def _seed(db: Database) -> None:
    now = now_str()
    with db.lock:
        db.conn.execute(f"DELETE FROM {TABLE_NAME}")
        rows = [
            (
                "s1",
                "SN-PERF-001",
                "客户A",
                "CH-SEA",
                "CAR-A",
                "LAX",
                "2026-01-01 00:00:00",
                "2026-01-02 00:00:00",
                "2026-01-20 00:00:00",
                "2026-01-22 00:00:00",
                "2026-02-01 00:00:00",
                "2026-02-05 00:00:00",
                now,
                now,
            ),
            (
                "s2",
                "SN-PERF-002",
                "客户A",
                "CH-SEA",
                "CAR-A",
                "LAX",
                "2026-02-01 00:00:00",
                "2026-02-03 00:00:00",
                "2026-02-25 00:00:00",
                "2026-03-01 00:00:00",
                "2026-03-10 00:00:00",
                "2026-03-20 00:00:00",
                now,
                now,
            ),
            (
                "s3",
                "SN-PERF-003",
                "客户B",
                "CH-AIR",
                "CAR-B",
                "JFK",
                "2026-03-01 00:00:00",
                "2026-03-01 00:00:00",
                "2026-03-15 00:00:00",
                "2026-03-20 00:00:00",
                "2026-03-25 00:00:00",
                "2026-04-10 00:00:00",
                now,
                now,
            ),
        ]
        for row in rows:
            db.conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, shipment_no, customer, channel_code, carrier_code,
                    destination_port_code, etd, atd, eta, ata,
                    expected_delivery_time, delivered_time, created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )
        db.conn.commit()


def test_performance_analysis_metrics(tmp_path: Path) -> None:
    db = Database(tmp_path / "perf.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    _seed(db)
    repo = ShipmentPerformanceStatisticsRepository(db)

    result = repo.analyze(ShipmentPerformanceQuery(date_basis="atd"))
    overview = result["overview"]
    assert result["analyzedCount"] == 3
    assert overview["signedCount"] == 3
    assert overview["fullTransit"]["sampleCount"] == 3
    assert overview["fullTransit"]["minDays"] == 34
    assert overview["fullTransit"]["maxDays"] == 45
    assert overview["fastestSignedTransitDays"] == 34
    assert overview["fastestSignedShipmentNo"] == "SN-PERF-001"
    assert overview["slowestSignedTransitDays"] == 45
    assert overview["slowestSignedShipmentNo"] == "SN-PERF-002"
    assert overview["seaTransit"]["sampleCount"] == 3
    assert len(result["byChannel"]) == 2
    assert len(result["byCarrier"]) == 2
    assert len(result["byCustomer"]) == 2

    filtered = repo.analyze(
        ShipmentPerformanceQuery(date_basis="atd", channel_code="CH-SEA", customer="客户A")
    )
    assert filtered["analyzedCount"] == 2

    details = repo.details(ShipmentPerformanceQuery(), page=1, page_size=10)
    assert details["total"] == 3
    assert details["items"][0]["shipmentNo"]

    csv_text, _ = repo.export_csv(ShipmentPerformanceQuery())
    assert "SN-PERF-001" in csv_text
