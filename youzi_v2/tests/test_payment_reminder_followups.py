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
                    id, shipment_no, customer, customer_no, ref_shipment_no, etd, payment_status,
                    created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sid, "PAY-R-001", "客户A", "PO-1", "REF-001", "2026-07-01", "UNPAID", now, now),
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
    assert row["refShipmentNo"] == "REF-001"
    assert row["isFcl"] is False
    assert row["followupCount"] == 1
    assert row["lastFollowupNote"] == "已电话催款"

    history = repo.list_followups(sid)
    assert len(history) == 1


def test_list_reminders_fcl_exposes_bill_and_container(tmp_path: Path) -> None:
    repo, db = _prepare_repo(tmp_path)
    _seed(db, fcl=True)

    listed = repo.list_reminders(scope="overdue", fcl_only=True, limit=20, offset=0)
    row = next(i for i in listed["items"] if i["shipmentNo"] == "FCL-PAY-001")
    assert row["isFcl"] is True
    assert row["billOfLadingNo"] == "OOLU2169890590"
    assert row["containerNo"] == "CONT9876543"
    assert row["customerNo"] == "PO-FCL"


def test_list_reminders_fcl_only_filter(tmp_path: Path) -> None:
    repo, db = _prepare_repo(tmp_path)
    _seed(db)
    now = "2026-07-11 12:00:00"
    fcl_sid = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, customer, customer_no, channel_code,
                bill_of_lading_no, container_no, etd, payment_status,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fcl_sid,
                "FCL-PAY-002",
                "客户A",
                "PO-FCL2",
                "FC-整柜",
                "OOLU2169890591",
                "CONT111",
                "2026-07-01",
                "UNPAID",
                now,
                now,
            ),
        )
        db.conn.commit()

    exclude = repo.list_reminders(scope="all_unpaid", fcl_only=False, limit=50, offset=0)
    nos = {i["shipmentNo"] for i in exclude["items"]}
    assert "PAY-R-001" in nos
    assert "FCL-PAY-002" not in nos

    only_fcl = repo.list_reminders(scope="all_unpaid", fcl_only=True, limit=50, offset=0)
    nos_fcl = {i["shipmentNo"] for i in only_fcl["items"]}
    assert "FCL-PAY-002" in nos_fcl
    assert "PAY-R-001" not in nos_fcl

    summary = repo.reminder_summary(fcl_only=False)
    assert summary["allUnpaidCount"] >= 1
    summary_fcl = repo.reminder_summary(fcl_only=True)
    assert summary_fcl["allUnpaidCount"] >= 1
    assert "PAY-R-001" not in {
        i["shipmentNo"]
        for i in repo.list_reminders(scope="all_unpaid", fcl_only=True, limit=50)["items"]
    }

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
    from io import BytesIO

    from openpyxl import load_workbook

    from youzi_v2.services.payment_reminder_excel import build_payment_reminder_export_bytes

    repo, db = _prepare_repo(tmp_path)
    _seed(db)
    listed = repo.list_reminders(scope="all_unpaid", limit=20, offset=0)
    # 补一条带 ATA / 签收时间的明细用于导出断言
    items = list(listed["items"])
    if items:
        items[0] = {
            **items[0],
            "ata": "2026-06-20 08:00:00",
            "deliveredTime": "2026-06-25 19:30:00",
        }
    data = build_payment_reminder_export_bytes(items)
    assert data[:2] == b"PK"
    wb = load_workbook(BytesIO(data))
    headers = [c.value for c in wb.active[1]]
    assert "ATA" in headers
    assert "签收日期" in headers
    assert "关联单号" in headers
    row = {headers[i]: wb.active[2][i].value for i in range(len(headers))}
    assert row["ATA"] == "2026-06-20"
    assert row["签收日期"] == "2026-06-25"
    assert row["关联单号"] == "REF-001"

