"""已付款运单修改锁定。"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from youzi_v2.db.connection import Database
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE, ensure_schema
from youzi_v2.db.shipments_repository import (
    PAID_SHIPMENT_LOCKED_MSG,
    PaidShipmentLockedError,
    ShipmentsRepository,
)
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


def test_paid_shipment_blocks_general_update(tmp_path: Path) -> None:
    db = Database(tmp_path / "paid.db")
    ensure_schema(db.conn)
    repo, sid, _ = _seed_paid(db)
    with pytest.raises(PaidShipmentLockedError) as exc:
        repo.update_row(sid, {"customer": "新客户"})
    assert PAID_SHIPMENT_LOCKED_MSG in str(exc.value)


def test_paid_shipment_allows_unpay_from_shipment_list(tmp_path: Path) -> None:
    db = Database(tmp_path / "paid2.db")
    ensure_schema(db.conn)
    repo, sid, _ = _seed_paid(db)
    row = repo.update_row(sid, {"payment_status": "UNPAID"}, allow_paid_unpay=True)
    assert row["paymentStatus"] == "UNPAID"


def test_paid_shipment_blocks_mixed_unpay_and_other_fields(tmp_path: Path) -> None:
    db = Database(tmp_path / "paid3.db")
    ensure_schema(db.conn)
    repo, sid, _ = _seed_paid(db)
    with pytest.raises(PaidShipmentLockedError):
        repo.update_row(
            sid,
            {"payment_status": "UNPAID", "customer": "新客户"},
            allow_paid_unpay=True,
        )


def test_dps_upsert_skips_paid_shipment(tmp_path: Path) -> None:
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
    row, changed = repo.upsert_by_shipment_no(filtered)
    assert changed is False
    assert row["customer"] == "客户A"
    assert row["paymentStatus"] == "PAID"


def test_tracking_summary_skips_paid_shipment(tmp_path: Path) -> None:
    db = Database(tmp_path / "paid5.db")
    ensure_schema(db.conn)
    repo, _, sn = _seed_paid(db)
    repo.update_internal_tracking_summary(sn, "2026-07-11 10:00:00", "测试轨迹")
    row = repo.get_by_shipment_no(sn)
    assert row is not None
    assert not (row.get("latestTrackingDesc") or "").strip()
