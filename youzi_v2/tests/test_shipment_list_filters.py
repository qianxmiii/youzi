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


def test_batch_search_matches_shipment_no(tmp_path: Path) -> None:
    db = Database(tmp_path / "kw.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    repo = ShipmentsRepository(db)
    _insert(db, shipment_no="ABC-999")
    _insert(db, shipment_no="OTHER-1")

    res = repo.list_rows(shipment_nos=["ABC-999"])
    assert res["total"] == 1
    assert res["items"][0]["shipmentNo"] == "ABC-999"


def test_keyword_search_matches_supplier_only(tmp_path: Path) -> None:
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
                customer_no, bill_of_lading_no, container_no, carrier_id, tracking_number,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                "SN-KW-1",
                "深圳某某供应商",
                "FBA123456789",
                "PO-9988",
                "BL-2026001",
                "CONT9876543",
                "LEGACY-BL",
                "LEGACY-CONT",
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
    assert repo.list_rows(shipment_nos=["FBA123456789"])["total"] == 1
    assert repo.list_rows(shipment_nos=["PO-9988"])["total"] == 1
    assert repo.list_rows(bill_nos=["BL-2026001"])["total"] == 1
    assert repo.list_rows(container_nos=["CONT9876543"])["total"] == 1
    assert repo.list_rows(search="FBA123456789")["total"] == 0


def test_unified_batch_number_search(tmp_path: Path) -> None:
    db = Database(tmp_path / "batch.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    repo = ShipmentsRepository(db)
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, customer_shipment_id, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-A", "FBA-001", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, customer_shipment_id, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-B", "FBA-002", now, now),
        )
        db.conn.commit()

    res = repo.list_rows(shipment_nos=["SN-A", "FBA-002"])
    assert res["total"] == 2
    nos = {row["shipmentNo"] for row in res["items"]}
    assert nos == {"SN-A", "SN-B"}


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


def test_has_tracking_number_filter(tmp_path: Path) -> None:
    from youzi_v2.db.shipment_tracking_numbers_table import (
        TABLE_NAME as STN_TABLE,
        ensure_schema as ensure_stn_schema,
    )

    db = Database(tmp_path / "tn.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    ensure_stn_schema(db.conn)
    repo = ShipmentsRepository(db)
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, tracking_number, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-TN-1", "1Z999AA10123456784", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, tracking_number, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-TN-2", "", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, tracking_number, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-TN-3", "", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {STN_TABLE} (
                id, shipment_no, main_tracking_number, tracking_number,
                is_main, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-TN-3", "CW-MAIN", "CW-SUB-001", 0, now, now),
        )
        db.conn.commit()

    res = repo.list_rows(has_tracking_number=True, limit=50)
    assert res["total"] == 2
    nos = {row["shipmentNo"] for row in res["items"]}
    assert nos == {"SN-TN-1", "SN-TN-3"}


def test_tracking_search_matches_tokens_across_nbsp(tmp_path: Path) -> None:
    from youzi_v2.db.internal_tracking_logs_table import ensure_schema as ensure_logs_schema
    from youzi_v2.db.shipment_list_filters import tracking_search_like_pattern

    assert tracking_search_like_pattern("COSCO THAILAND") == "%COSCO%THAILAND%"

    db = Database(tmp_path / "track_search.db")
    ensure_shipments_schema(db.conn)
    ensure_logs_schema(db.conn)
    now = now_str()
    ship_no = "DPSECO260617048"
    desc = (
        "Loaded into container（已装柜配载，ETD:2026-06-25,ETA:2026-07-24,"
        "船名航次：COSCO\xa0THAILAND/115E）"
    )
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, status_code, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), ship_no, "IN_TRANSIT", now, now),
        )
        db.conn.execute(
            """
            INSERT INTO internal_tracking_logs (
                id, shipment_no, tracking_time, tracking_desc, created_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), ship_no, "2026-06-20 10:00:00", desc, now),
        )
        db.conn.commit()

    repo = ShipmentsRepository(db)
    res = repo.list_rows(
        tracking_search="COSCO THAILAND",
        status_code="IN_TRANSIT",
        limit=20,
    )
    assert res["total"] == 1
    assert res["items"][0]["shipmentNo"] == ship_no


def test_fcl_only_filter(tmp_path: Path) -> None:
    db = Database(tmp_path / "fcl.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, carrier_code, channel_code, status_code,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "FCL-1", "整柜", "", "IN_TRANSIT", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, carrier_code, channel_code, status_code,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "FCL-2", "", "FC-整柜", "IN_TRANSIT", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, carrier_code, channel_code, status_code,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "EXP-1", "FedEx", "SER-LAX", "IN_TRANSIT", now, now),
        )
        db.conn.commit()

    repo = ShipmentsRepository(db)
    only_fcl = repo.list_rows(fcl_only=True, limit=20)
    assert only_fcl["total"] == 2
    assert {i["shipmentNo"] for i in only_fcl["items"]} == {"FCL-1", "FCL-2"}

    exclude_fcl = repo.list_rows(fcl_only=False, limit=20)
    assert exclude_fcl["total"] == 1
    assert exclude_fcl["items"][0]["shipmentNo"] == "EXP-1"


def test_payment_status_filter(tmp_path: Path) -> None:
    db = Database(tmp_path / "payment.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    repo = ShipmentsRepository(db)
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, payment_status, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "PAY-PAID", "PAID", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, payment_status, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "PAY-UNPAID", "UNPAID", now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, created_time, updated_time
            ) VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "PAY-EMPTY", now, now),
        )
        db.conn.commit()

    paid = repo.list_rows(payment_status="PAID", limit=10)
    assert paid["total"] == 1
    assert paid["items"][0]["shipmentNo"] == "PAY-PAID"

    unpaid = repo.list_rows(payment_status="UNPAID", limit=10)
    assert unpaid["total"] == 1
    assert unpaid["items"][0]["shipmentNo"] == "PAY-UNPAID"

    empty = repo.list_rows(payment_status="__EMPTY__", limit=10)
    assert empty["total"] == 1
    assert empty["items"][0]["shipmentNo"] == "PAY-EMPTY"
