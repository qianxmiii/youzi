"""已付款运单可正常修改（无字段锁定）。"""

from __future__ import annotations

import uuid
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE, ensure_schema
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.services.shipment_dps_mapper import dps_row_to_shipment
from youzi_v2.services.shipment_dps_sync_fields import filter_dps_payload
from youzi_v2.tests.test_shipment_dps_sync import SAMPLE_DELIVERED


def _seed_paid(db: Database) -> tuple[ShipmentsRepository, str, str]:
    now = "2026-07-11 12:00:00"
    sid = str(uuid.uuid4())
    sn = "PAID-LOCK-001"
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, customer, payment_status, created_time, updated_time
            ) VALUES (?, ?, '客户A', 'PAID', ?, ?)
            """,
            (sid, sn, now, now),
        )
        db.conn.commit()
    return ShipmentsRepository(db), sid, sn


def test_paid_shipment_allows_general_update(tmp_path: Path) -> None:
    db = Database(tmp_path / "paid.db")
    ensure_schema(db.conn)
    repo, sid, _ = _seed_paid(db)
    row = repo.update_row(sid, {"customer": "新客户", "channel_code": "STE-LAX"})
    assert row["customer"] == "新客户"
    assert row["channelCode"] == "STE-LAX"
    assert row["paymentStatus"] == "PAID"


def test_paid_shipment_allows_unpay_and_other_fields(tmp_path: Path) -> None:
    db = Database(tmp_path / "paid2.db")
    ensure_schema(db.conn)
    repo, sid, _ = _seed_paid(db)
    row = repo.update_row(
        sid,
        {"payment_status": "UNPAID", "customer": "新客户"},
    )
    assert row["paymentStatus"] == "UNPAID"
    assert row["customer"] == "新客户"


def test_dps_upsert_updates_paid_shipment(tmp_path: Path) -> None:
    db = Database(tmp_path / "paid4.db")
    ensure_schema(db.conn)
    repo, _, sn = _seed_paid(db)
    payload = dps_row_to_shipment(
        {
            **SAMPLE_DELIVERED,
            "odd": sn,
            "clientUserNickName": "DPS客户",
            "clientVerifyStatus": 0,
        }
    )
    assert payload is not None
    filtered = filter_dps_payload(payload, is_new=False)
    row, created = repo.upsert_by_shipment_no(filtered)
    assert created is False
    assert row["customer"] == "DPS客户"
    # 本地已付款时 DPS 不同步覆盖为未付款（付款状态回填规则仍保留）
    assert row["paymentStatus"] == "PAID"


def test_paid_shipment_allows_internal_tracking_summary(tmp_path: Path) -> None:
    db = Database(tmp_path / "paid5.db")
    ensure_schema(db.conn)
    repo, _, sn = _seed_paid(db)
    repo.update_internal_tracking_summary(
        sn,
        "2026-07-11 10:00:00",
        "Your goods have been signed for",
        status_code="DELIVERED",
    )
    row = repo.get_by_shipment_no(sn)
    assert row is not None
    assert row["latestTrackingDesc"] == "Your goods have been signed for"
    assert row["statusCode"] == "DELIVERED"


def test_paid_shipment_allows_carrier_id_and_tracking_number(tmp_path: Path) -> None:
    db = Database(tmp_path / "paid6.db")
    ensure_schema(db.conn)
    repo, _, sn = _seed_paid(db)
    assert repo.set_carrier_id(sn, "CID-001") is True
    assert repo.set_tracking_number(sn, "1Z999") is True
    row = repo.get_by_shipment_no(sn)
    assert row is not None
    assert row["carrierId"] == "CID-001"
    assert row["trackingNumber"] == "1Z999"
