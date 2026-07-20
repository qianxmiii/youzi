"""报价跟进规则与仓储测试。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.quote_followups_table import ensure_schema as ensure_followups
from youzi_v2.db.quote_opportunities_repository import QuoteOpportunitiesRepository
from youzi_v2.db.quote_opportunities_table import ensure_schema as ensure_opps
from youzi_v2.db.quote_versions_table import ensure_schema as ensure_versions
from youzi_v2.services.quote_followup_rules import (
    compute_next_followup_date,
    display_status,
    matches_scope,
)


def _repo(tmp_path: Path) -> QuoteOpportunitiesRepository:
    db = Database(tmp_path / "quote.db")
    ensure_opps(db.conn)
    ensure_versions(db.conn)
    ensure_followups(db.conn)
    return QuoteOpportunitiesRepository(db)


def test_compute_next_followup_respects_deadline() -> None:
    assert (
        compute_next_followup_date(
            base_day=date(2026, 7, 10),
            interval_days=1,
            deadline=date(2026, 7, 10),
        )
        == ""
    )
    assert (
        compute_next_followup_date(
            base_day=date(2026, 7, 10),
            interval_days=1,
            deadline=date(2026, 7, 20),
        )
        == "2026-07-11"
    )


def test_display_status_expired_without_db_change() -> None:
    assert display_status("FOLLOWING", date(2026, 7, 1), date(2026, 7, 13)) == "EXPIRED"
    assert display_status("WON", date(2026, 7, 1), date(2026, 7, 13)) == "WON"


def test_matches_scope_todo() -> None:
    assert matches_scope(
        status="FOLLOWING",
        display_status_value="FOLLOWING",
        next_followup=date(2026, 7, 10),
        deadline=date(2026, 7, 20),
        scope="todo",
        today=date(2026, 7, 13),
    )
    assert not matches_scope(
        status="FOLLOWING",
        display_status_value="FOLLOWING",
        next_followup=date(2026, 7, 20),
        deadline=date(2026, 8, 1),
        scope="todo",
        today=date(2026, 7, 13),
    )


def test_create_followup_and_adjust_quote(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    created = repo.create(
        {
            "customer_name": "客户A",
            "is_new_customer": True,
            "quote_date": "2026-07-13",
            "deadline_date": "2026-07-30",
            "followup_interval_days": 1,
            "quoted_amount": 1800,
            "quoted_currency": "USD",
            "profit_amount": 120,
            "profit_currency": "USD",
            "profit_rate": 18,
            "product_name": "日用品",
        }
    )
    assert created["quoteNo"].startswith("QT")
    assert created["status"] == "QUOTED"
    assert created["currentQuotedAmount"] == 1800

    versions = repo.list_versions(created["id"])
    assert len(versions) == 1
    assert versions[0]["changeReason"] == "INITIAL"

    fu = repo.create_followup(
        created["id"],
        followup_type="wechat",
        note="客户嫌贵",
        next_followup_date="2026-07-16",
        adjust_quote=True,
        version={
            "change_reason": "PRICE_DOWN",
            "quoted_amount": 1650,
            "quoted_currency": "USD",
            "profit_amount": 90,
            "profit_currency": "USD",
            "profit_rate": 13,
            "note": "降价",
        },
    )
    assert fu["note"] == "客户嫌贵"

    updated = repo.get_by_id(created["id"])
    assert updated is not None
    assert updated["status"] == "FOLLOWING"
    assert updated["currentQuotedAmount"] == 1650
    assert updated["followupCount"] == 1
    assert len(repo.list_versions(created["id"])) == 2

    won = repo.mark_won(created["id"])
    assert won["status"] == "WON"

    listed = repo.list_rows(scope="won", limit=20)
    assert any(i["id"] == created["id"] for i in listed["items"])


def test_notification_summary(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    today = date.today().isoformat()
    repo.create(
        {
            "customer_name": "B",
            "is_new_customer": True,
            "quote_date": today,
            "deadline_date": today,
            "followup_interval_days": 1,
            "next_followup_date": today,
        }
    )
    summary = repo.notification_summary()
    assert summary["pendingCount"] >= 1
    assert summary["todayCount"] >= 1 or summary["expiringSoonCount"] >= 1
