"""催款规则计算测试。"""

from __future__ import annotations

from datetime import date

import unittest

from youzi_v2.services.payment_reminder_rules import (
    SETTLEMENT_AFTER_ARRIVAL,
    SETTLEMENT_BEFORE_ARRIVAL,
    SETTLEMENT_BEFORE_SHIPMENT,
    SETTLEMENT_MONTHLY,
    compute_payment_reminder,
    matches_scope,
    monthly_due_date,
)


class PaymentReminderRulesTest(unittest.TestCase):
    def test_monthly_due_date_end_of_month(self) -> None:
        self.assertEqual(monthly_due_date(date(2026, 1, 15), 31), date(2026, 2, 28))
        self.assertEqual(monthly_due_date(date(2026, 4, 1), 31), date(2026, 5, 31))

    def test_before_shipment_upcoming(self) -> None:
        row = {"etd": "2026-07-20"}
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_SHIPMENT,
            settlement_day=None,
            today=date(2026, 7, 13),
        )
        self.assertEqual(out["reminderType"], "upcoming_7_days")
        self.assertEqual(out["dueDate"], "2026-07-20")

    def test_before_shipment_overdue(self) -> None:
        row = {"etd": "2026-07-01"}
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_SHIPMENT,
            settlement_day=None,
            today=date(2026, 7, 11),
        )
        self.assertEqual(out["reminderType"], "overdue")

    def test_before_arrival_overdue_when_past_eta(self) -> None:
        row = {"eta": "2026-07-01", "ata": None}
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_ARRIVAL,
            settlement_day=None,
            today=date(2026, 7, 11),
        )
        self.assertEqual(out["reminderType"], "overdue")
        self.assertEqual(out["dueDate"], "2026-07-01")
        self.assertEqual(out["overdueDays"], 10)

    def test_long_overdue_uses_delivered_time_after_15_days(self) -> None:
        row = {
            "eta": "2026-06-01",
            "ata": "2026-06-10",
            "delivered_time": "2026-06-29 19:00:00",
        }
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_ARRIVAL,
            settlement_day=None,
            today=date(2026, 7, 11),
        )
        self.assertEqual(out["reminderType"], "overdue")
        self.assertEqual(out["overdueDays"], 12)

    def test_long_overdue_keeps_regular_when_no_delivered_time(self) -> None:
        row = {"eta": "2026-06-01", "ata": "2026-06-10"}
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_ARRIVAL,
            settlement_day=None,
            today=date(2026, 7, 11),
        )
        self.assertEqual(out["overdueDays"], 40)

    def test_long_overdue_not_applied_within_15_days(self) -> None:
        row = {
            "eta": "2026-07-01",
            "delivered_time": "2026-06-20",
        }
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_ARRIVAL,
            settlement_day=None,
            today=date(2026, 7, 11),
        )
        self.assertEqual(out["overdueDays"], 10)

    def test_before_arrival_ata_early_uses_eta_due(self) -> None:
        row = {"eta": "2026-07-20", "ata": "2026-07-18"}
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_ARRIVAL,
            settlement_day=None,
            today=date(2026, 7, 19),
        )
        self.assertEqual(out["reminderType"], "overdue")
        self.assertEqual(out["dueDate"], "2026-07-20")
        self.assertEqual(out["baseDate"], "2026-07-20")
        self.assertEqual(out["overdueDays"], 0)
        self.assertEqual(out["daysUntilDue"], 0)

    def test_before_arrival_ata_on_eta_day(self) -> None:
        row = {"eta": "2026-07-20", "ata": "2026-07-20"}
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_ARRIVAL,
            settlement_day=None,
            today=date(2026, 7, 20),
        )
        self.assertEqual(out["reminderType"], "today")
        self.assertEqual(out["dueDate"], "2026-07-20")

    def test_before_shipment_window_boundaries(self) -> None:
        row = {"etd": "2026-07-20"}
        before = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_SHIPMENT,
            settlement_day=None,
            today=date(2026, 7, 12),
        )
        start = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_BEFORE_SHIPMENT,
            settlement_day=None,
            today=date(2026, 7, 13),
        )
        self.assertEqual(before["reminderType"], "")
        self.assertFalse(matches_scope(before["reminderType"], "todo"))
        self.assertEqual(start["reminderType"], "upcoming_7_days")
        self.assertEqual(start["daysUntilDue"], 7)

    def test_after_arrival_today(self) -> None:
        row = {"ata": "2026-07-11"}
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_AFTER_ARRIVAL,
            settlement_day=None,
            today=date(2026, 7, 11),
        )
        self.assertEqual(out["reminderType"], "today")

    def test_monthly_due(self) -> None:
        row = {"warehouse_entry_time": "2026-06-15 10:00:00"}
        out = compute_payment_reminder(
            row,
            settlement_method=SETTLEMENT_MONTHLY,
            settlement_day=5,
            today=date(2026, 7, 5),
        )
        self.assertEqual(out["reminderType"], "monthly")
        self.assertEqual(out["dueDate"], "2026-07-05")

    def test_missing_rule_without_settlement(self) -> None:
        out = compute_payment_reminder(
            {"etd": "2026-07-01"},
            settlement_method=None,
            settlement_day=None,
            today=date(2026, 7, 11),
        )
        self.assertEqual(out["reminderType"], "missing_rule")

    def test_matches_scope_todo(self) -> None:
        self.assertTrue(matches_scope("overdue", "todo"))
        self.assertTrue(matches_scope("missing_rule", "todo"))
        self.assertFalse(matches_scope("missing_date", "todo"))
        self.assertFalse(matches_scope("", "todo"))
