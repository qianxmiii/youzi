"""运单列表筛选 SQL 片段测试。"""

from __future__ import annotations

import uuid
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_groups_table import ensure_schema as ensure_group_schema
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.shipments_table import TABLE_NAME, ensure_schema as ensure_shipments_schema


def _insert(
    db: Database,
    *,
    shipment_no: str,
    carrier_code: str = "",
    expected_delivery_time: str = "",
    delivered_time: str = "",
    ata: str = "",
    status_code: str = "IN_TRANSIT",
) -> None:
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, carrier_code, expected_delivery_time,
                delivered_time, ata, status_code, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                shipment_no,
                carrier_code,
                expected_delivery_time,
                delivered_time,
                ata,
                status_code,
                now,
                now,
            ),
        )
        db.conn.commit()


def test_keyword_search_matches_shipment_no(tmp_path: Path) -> None:
    db = Database(tmp_path / "kw.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    repo = ShipmentsRepository(db)
    _insert(db, shipment_no="ABC-999")
    _insert(db, shipment_no="OTHER-1")

    res = repo.list_rows(search="ABC-999")
    assert res["total"] == 1
    assert res["items"][0]["shipmentNo"] == "ABC-999"


def test_keyword_search_matches_supplier_and_shipment_id(tmp_path: Path) -> None:
    db = Database(tmp_path / "kw2.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    repo = ShipmentsRepository(db)
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, supplier_name, customer_shipment_id,
                customer_no, carrier_id, tracking_number,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                "SN-KW-1",
                "深圳某某供应商",
                "FBA123456789",
                "PO-9988",
                "BL-2026001",
                "CONT9876543",
                now,
                now,
            ),
        )
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, created_time, updated_time
            ) VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-KW-2", now, now),
        )
        db.conn.commit()

    assert repo.list_rows(search="某某供应商")["total"] == 1
    assert repo.list_rows(search="FBA123456789")["total"] == 1
    assert repo.list_rows(search="PO-9988")["total"] == 1
    assert repo.list_rows(search="BL-2026001")["total"] == 1
    assert repo.list_rows(search="CONT9876543")["total"] == 1


def test_time_field_atd_range(tmp_path: Path) -> None:
    db = Database(tmp_path / "atd.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    repo = ShipmentsRepository(db)
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, atd, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-1", "2026-06-10 08:00:00", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, atd, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-2", "2026-07-01 08:00:00", now, now),
        )
        db.conn.commit()

    res = repo.list_rows(
        time_field="atd",
        time_from="2026-06-01",
        time_to="2026-06-30",
    )
    assert res["total"] == 1
    assert res["items"][0]["shipmentNo"] == "SN-1"


def test_delivery_risk_overdue(tmp_path: Path) -> None:
    from datetime import date, timedelta

    db = Database(tmp_path / "risk.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    repo = ShipmentsRepository(db)
    overdue_day = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d 00:00:00")
    _insert(
        db,
        shipment_no="OVER-1",
        expected_delivery_time=overdue_day,
    )
    _insert(
        db,
        shipment_no="OK-1",
        expected_delivery_time="2099-01-01 00:00:00",
    )

    res = repo.list_rows(delivery_risk="overdue")
    assert res["total"] == 1
    assert res["items"][0]["shipmentNo"] == "OVER-1"


def test_arrived_not_delivered(tmp_path: Path) -> None:
    db = Database(tmp_path / "arr.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    repo = ShipmentsRepository(db)
    _insert(db, shipment_no="ARR-1", ata="2026-06-01 08:00:00")
    _insert(
        db,
        shipment_no="DEL-1",
        ata="2026-06-01 08:00:00",
        delivered_time="2026-06-05 08:00:00",
        status_code="DELIVERED",
    )

    res = repo.list_rows(has_ata=True, not_delivered=True)
    assert res["total"] == 1
    assert res["items"][0]["shipmentNo"] == "ARR-1"
