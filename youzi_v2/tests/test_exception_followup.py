import unittest
from datetime import datetime, timedelta

from youzi_v2.db.exception_followup import (
    exception_days_open,
    followup_interval_days,
    followup_severity,
    is_followup_due,
)


class ExceptionFollowupLogicTest(unittest.TestCase):
    def test_interval_tiers(self) -> None:
        self.assertEqual(followup_interval_days(0), 3)
        self.assertEqual(followup_interval_days(9), 3)
        self.assertEqual(followup_interval_days(10), 5)
        self.assertEqual(followup_interval_days(19), 5)
        self.assertEqual(followup_interval_days(20), 7)

    def test_severity_tiers(self) -> None:
        self.assertEqual(followup_severity(5), "info")
        self.assertEqual(followup_severity(12), "warning")
        self.assertEqual(followup_severity(25), "urgent")

    def test_first_reminder_after_interval_from_open(self) -> None:
        opened = "2026-05-01 10:00:00"
        now = datetime(2026, 5, 3, 12, 0, 0)
        self.assertEqual(exception_days_open(opened, now=now), 2)
        due, days, interval = is_followup_due(opened, None, now=now)
        self.assertFalse(due)
        self.assertEqual(interval, 3)

        now3 = datetime(2026, 5, 4, 12, 0, 0)
        due, days, interval = is_followup_due(opened, None, now=now3)
        self.assertTrue(due)
        self.assertEqual(days, 3)
        self.assertEqual(interval, 3)

    def test_repeat_after_last_followup(self) -> None:
        opened = "2026-05-01 10:00:00"
        last = "2026-05-04 10:00:00"
        now = datetime(2026, 5, 6, 10, 0, 0)
        due, _, interval = is_followup_due(opened, last, now=now)
        self.assertFalse(due)
        self.assertEqual(interval, 3)

        now_ok = datetime(2026, 5, 7, 10, 0, 0)
        due, _, _ = is_followup_due(opened, last, now=now_ok)
        self.assertTrue(due)

    def test_tier_switch_uses_current_interval(self) -> None:
        opened = (datetime.now() - timedelta(days=11)).strftime("%Y-%m-%d %H:%M:%S")
        last = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        due, days, interval = is_followup_due(opened, last)
        self.assertFalse(due)
        self.assertGreaterEqual(days, 10)
        self.assertEqual(interval, 5)


if __name__ == "__main__":
    unittest.main()
