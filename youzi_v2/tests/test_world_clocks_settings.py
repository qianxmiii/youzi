"""顶栏世界时间配置。"""

import json
import tempfile
import unittest
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.services.world_clocks_settings import (
    KEY_ZONES,
    get_world_clocks_settings,
    save_world_clocks_settings,
)
from youzi_v2.db.app_settings_table import get_setting


class WorldClocksSettingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = Database(Path(self._tmp.name) / "test.db")

    def tearDown(self):
        self.db.conn.close()

    def test_defaults_include_beijing(self):
        cfg = get_world_clocks_settings(self.db)
        self.assertTrue(cfg.enabled)
        labels = [z.label for z in cfg.zones]
        self.assertIn("北京", labels)

    def test_save_and_reload(self):
        save_world_clocks_settings(
            self.db,
            enabled=True,
            use24h=True,
            zones=[
                {"tz": "Asia/Shanghai", "label": "北京"},
                {"tz": "Europe/Berlin", "label": "柏林"},
            ],
        )
        cfg = get_world_clocks_settings(self.db)
        self.assertEqual(len(cfg.zones), 2)
        self.assertEqual(cfg.zones[1].tz, "Europe/Berlin")

    def test_invalid_tz_skipped(self):
        save_world_clocks_settings(
            self.db,
            enabled=True,
            use24h=True,
            zones=[{"tz": "Not/A_Zone", "label": "X"}, {"tz": "Asia/Tokyo", "label": "东京"}],
        )
        with self.db.lock:
            raw = get_setting(self.db.conn, KEY_ZONES)
        data = json.loads(raw or "[]")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["tz"], "Asia/Tokyo")


if __name__ == "__main__":
    unittest.main()
