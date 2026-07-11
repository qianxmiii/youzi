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


def _seed(db: Database) -> str:
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


def test_list_reminders_and_followup(tmp_path: Path) -> None:
    db = Database(tmp_path / "pay.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    from youzi_v2.db.customers_table import ensure_schema as ensure_customers_schema
    from youzi_v2.db.shipment_payment_followups_table import ensure_schema as ensure_followups_schema

    ensure_customers_schema(db.conn)
    ensure_followups_schema(db.conn)
    sid = _seed(db)
    repo = ShipmentPaymentFollowupsRepository(db)

    listed = repo.list_reminders(scope="overdue", limit=20, offset=0)
    assert listed["total"] >= 1
    assert any(i["shipmentNo"] == "PAY-R-001" for i in listed["items"])

    fu = repo.create_followup(sid, note="已电话催款")
    assert fu["note"] == "已电话催款"

    listed2 = repo.list_reminders(scope="overdue", limit=20, offset=0)
    row = next(i for i in listed2["items"] if i["shipmentNo"] == "PAY-R-001")
    assert row["customerNo"] == "PO-1"
    assert row["followupCount"] == 1
    assert row["lastFollowupNote"] == "已电话催款"

    history = repo.list_followups(sid)
    assert len(history) == 1
