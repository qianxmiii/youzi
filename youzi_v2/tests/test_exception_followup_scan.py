"""异常跟进提醒扫描集成测试。"""
from __future__ import annotations

import uuid
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.shipment_exception_followup_repository import ShipmentExceptionFollowupRepository
from youzi_v2.db.shipment_exception_followup_table import ensure_schema as ensure_followup_schema
from youzi_v2.db.shipments_table import TABLE_NAME, ensure_schema as ensure_shipments_schema
from youzi_v2.services.exception_followup_reminders import scan_exception_followup_reminders


def _insert_shipment(db: Database, shipment_no: str, *, opened: str, exc: str = "DELAY") -> None:
    now = "2026-05-27 12:00:00"
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id, shipment_no, exception_code, exception_opened_time,
                created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), shipment_no, exc, opened, now, now),
        )
        db.conn.commit()


def test_scan_skips_when_scheduled_disabled(tmp_path: Path) -> None:
    db = Database(tmp_path / "disabled.db")
    ensure_shipments_schema(db.conn)
    ensure_followup_schema(db.conn)
    _insert_shipment(db, "YZ-FUP-002", opened="2026-05-01 10:00:00")
    repo = ShipmentExceptionFollowupRepository(db)

    result = scan_exception_followup_reminders(repo, force=False, trigger="scheduled")
    assert result["skipped"] is True
    assert result["created"] == 0
    assert repo.count_pending() == 0


def test_scan_creates_followup_when_due(tmp_path: Path) -> None:
    db = Database(tmp_path / "t.db")
    ensure_shipments_schema(db.conn)
    ensure_followup_schema(db.conn)
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shipment_exception_codes (
            code TEXT PRIMARY KEY, name_zh TEXT, name_en TEXT,
            sort_order INTEGER, is_active INTEGER, created_time TEXT, updated_time TEXT
        )
        """
    )
    db.conn.execute(
        "INSERT INTO shipment_exception_codes VALUES (?, ?, '', 0, 1, '', '')",
        ("DELAY", "延误"),
    )
    db.conn.commit()

    _insert_shipment(db, "YZ-FUP-001", opened="2026-05-01 10:00:00")
    repo = ShipmentExceptionFollowupRepository(db)

    result = scan_exception_followup_reminders(repo, force=True, trigger="manual")
    assert result["created"] == 1
    pending = repo.list_pending_notifications(limit=10)
    assert len(pending) == 1
    assert pending[0]["shipmentNo"] == "YZ-FUP-001"
    assert pending[0]["daysOpen"] >= 3
    assert "每" not in pending[0]["message"]
    assert "请跟进" in pending[0]["message"]

    result2 = scan_exception_followup_reminders(repo, force=True, trigger="manual")
    assert result2["created"] == 0

    repo.mark_resolved(pending[0]["id"])
    assert repo.count_pending() == 0
