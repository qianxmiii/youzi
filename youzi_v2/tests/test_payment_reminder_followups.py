"""催款跟进与列表集成测试。"""

from __future__ import annotations

import uuid
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.customers_table import TABLE_NAME as CUSTOMERS_TABLE
from youzi_v2.db.shipment_groups_table import ensure_schema as ensure_group_schema
from youzi_v2.db.shipment_payment_followups_repository import ShipmentPaymentFollowupsRepository
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE, ensure_schema as ensure_shipments_schema
from youzi_v2.services.payment_reminder_rules import SETTLEMENT_BEFORE_SHIPMENT


def _seed(db: Database, *, fcl: bool = False) -> str:
    now = "2026-07-11 12:00:00"
    sid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {CUSTOMERS_TABLE} (
                id, customer_name, track_query_lang, is_vip, note,
                settlement_method, settlement_day, shipment_count, created_time, updated_time
            ) VALUES (?, ?, 'zh', 0, '', ?, NULL, 0, ?, ?)
            """,
            (cid, "客户A", SETTLEMENT_BEFORE_SHIPMENT, now, now),
        )
        if fcl:
            db.conn.execute(
                f"""
                INSERT INTO {SHIPMENTS_TABLE} (
                    id, shipment_no, customer, customer_no, channel_code,
                    bill_of_lading_no, container_no, etd, payment_status,
                    created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    "FCL-PAY-001",
                    "客户A",
                    "PO-FCL",
                    "FC-整柜",
                    "OOLU2169890590",
                    "CONT9876543",
                    "2026-07-01",
                    "UNPAID",
                    now,
                    now,
                ),
            )
        else:
            db.conn.execute(
                f"""
                INSERT INTO {SHIPMENTS_TABLE} (
                    id, shipment_no, customer, customer_no, etd, payment_status,
                    created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sid, "PAY-R-001", "客户A", "PO-1", "2026-07-01", "UNPAID", now, now),
            )
        db.conn.commit()
    return sid


def _prepare_repo(tmp_path: Path) -> tuple[ShipmentPaymentFollowupsRepository, Database]:
    db = Database(tmp_path / "pay.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    from youzi_v2.db.customers_table import ensure_schema as ensure_customers_schema
    from youzi_v2.db.shipment_payment_followups_table import ensure_schema as ensure_followups_schema

    ensure_customers_schema(db.conn)
    ensure_followups_schema(db.conn)
    return ShipmentPaymentFollowupsRepository(db), db


def test_list_reminders_and_followup(tmp_path: Path) -> None:
    repo, db = _prepare_repo(tmp_path)
    sid = _seed(db)

    listed = repo.list_reminders(scope="overdue", limit=20, offset=0)
    assert listed["total"] >= 1
    assert any(i["shipmentNo"] == "PAY-R-001" for i in listed["items"])

    fu = repo.create_followup(sid, note="已电话催款")
    assert fu["note"] == "已电话催款"

    listed2 = repo.list_reminders(scope="overdue", limit=20, offset=0)
    row = next(i for i in listed2["items"] if i["shipmentNo"] == "PAY-R-001")
    assert row["customerNo"] == "PO-1"
    assert row["isFcl"] is False
    assert row["followupCount"] == 1
    assert row["lastFollowupNote"] == "已电话催款"

    history = repo.list_followups(sid)
    assert len(history) == 1


def test_list_reminders_fcl_exposes_bill_and_container(tmp_path: Path) -> None:
    repo, db = _prepare_repo(tmp_path)
    _seed(db, fcl=True)

    listed = repo.list_reminders(scope="overdue", limit=20, offset=0)
    row = next(i for i in listed["items"] if i["shipmentNo"] == "FCL-PAY-001")
    assert row["isFcl"] is True
    assert row["billOfLadingNo"] == "OOLU2169890590"
    assert row["containerNo"] == "CONT9876543"
    assert row["customerNo"] == "PO-FCL"

def test_list_reminders_followup_status_filter(tmp_path: Path) -> None:
    repo, db = _prepare_repo(tmp_path)
    sid = _seed(db)

    unfollowed = repo.list_reminders(
        scope="overdue", followup_status="unfollowed", limit=20, offset=0
    )
    assert any(i["shipmentNo"] == "PAY-R-001" for i in unfollowed["items"])
    followed = repo.list_reminders(
        scope="overdue", followup_status="followed", limit=20, offset=0
    )
    assert not any(i["shipmentNo"] == "PAY-R-001" for i in followed["items"])

    repo.create_followup(sid, note="已催")
    unfollowed2 = repo.list_reminders(
        scope="overdue", followup_status="unfollowed", limit=20, offset=0
    )
    followed2 = repo.list_reminders(
        scope="overdue", followup_status="followed", limit=20, offset=0
    )
    assert not any(i["shipmentNo"] == "PAY-R-001" for i in unfollowed2["items"])
    assert any(i["shipmentNo"] == "PAY-R-001" for i in followed2["items"])


def test_reminder_summary_counts(tmp_path: Path) -> None:
    repo, db = _prepare_repo(tmp_path)
    _seed(db)
    summary = repo.reminder_summary()
    assert summary["allUnpaidCount"] >= 1
    assert summary["todoCount"] >= 1
    assert "overdueCount" in summary


def test_build_payment_reminder_export_bytes(tmp_path: Path) -> None:
    from youzi_v2.services.payment_reminder_excel import build_payment_reminder_export_bytes

    repo, db = _prepare_repo(tmp_path)
    _seed(db)
    listed = repo.list_reminders(scope="all_unpaid", limit=20, offset=0)
    data = build_payment_reminder_export_bytes(listed["items"])
    assert data[:2] == b"PK"

