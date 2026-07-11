"""轨迹新鲜度 SQL 条件。"""

import unittest

from youzi_v2.db.tracking_freshness import (
    carrier_ahead_of_internal_sql,
    carrier_freshness_sql,
    freshness_stats_sql,
    internal_freshness_sql,
    internal_stale_days_sql,
    validate_freshness,
)
from youzi_v2.internal_tracking import INTERNAL_WAREHOUSE_PLACEHOLDER


class TrackingFreshnessTest(unittest.TestCase):
    def test_validate_freshness(self) -> None:
        self.assertEqual(validate_freshness("today"), "today")
        with self.assertRaises(ValueError):
            validate_freshness("invalid")

    def test_internal_today_sql_uses_localtime(self) -> None:
        sql, params = internal_freshness_sql("today")
        self.assertIn("date('now', 'localtime')", sql)
        self.assertEqual(len(params), 1)

    def test_carrier_within3d_sql(self) -> None:
        sql, _ = carrier_freshness_sql("within3d")
        self.assertIn("latest_carrier_time", sql)
        self.assertIn("-2 days", sql)

    def test_carrier_ahead_sql(self) -> None:
        sql, params = carrier_ahead_of_internal_sql("s")
        self.assertIn("latest_carrier_time", sql)
        self.assertIn("latest_tracking_time", sql)
        self.assertIn("+1 minutes", sql)
        self.assertEqual(len(params), 1)

    def test_carrier_none_sql_excludes_fcl(self) -> None:
        sql, params = carrier_freshness_sql("none")
        self.assertIn("carrier_code", sql)
        self.assertIn("整柜", params[0])
        self.assertEqual(len(params), 2)

    def test_internal_stale_days_sql(self) -> None:
        sql, params = internal_stale_days_sql(7)
        self.assertIn("latest_tracking_time", sql)
        self.assertIn("localtime", sql)
        self.assertIn("IN_TRANSIT", sql)
        self.assertEqual(params[1], "-7 days")
        self.assertEqual(params[0], INTERNAL_WAREHOUSE_PLACEHOLDER)

    def test_freshness_stats_sql_binding_count(self) -> None:
        sql, params = freshness_stats_sql()
        self.assertEqual(sql.count("?"), len(params))
        self.assertIn("carrier_codes", sql)
        self.assertIn("internal_stale_7d", sql)
        self.assertIn("internal_stale_14d", sql)
        self.assertEqual(params.count(INTERNAL_WAREHOUSE_PLACEHOLDER), 7)
        self.assertEqual(params.count("整柜"), 2)


if __name__ == "__main__":
    unittest.main()
