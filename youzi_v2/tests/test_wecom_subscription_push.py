"""订阅更新企微推送。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from youzi_v2.services.wecom_subscription_push import (
    format_subscription_push_message,
    read_subscription_push_enabled,
    try_push_subscription_notification,
)


class WecomSubscriptionPushTest(unittest.TestCase):
    def test_format_message(self) -> None:
        text = format_subscription_push_message(
            {
                "shipmentNo": "DPSECO1",
                "trackingSource": "internal",
                "latestTime": "2026-06-02 10:00:00",
                "latestDesc": "已到港",
            }
        )
        self.assertIn("【订阅更新】DPSECO1", text)
        self.assertIn("内部轨迹", text)
        self.assertIn("已到港", text)

    def test_subscription_push_default_on_when_wecom_enabled(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps({"wecom_webhook": {"enabled": True, "key": "k"}}),
            encoding="utf-8",
        )
        self.assertTrue(read_subscription_push_enabled(cfg_path))
        tmp.cleanup()

    def test_subscription_push_explicit_off(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "wecom_webhook": {
                        "enabled": True,
                        "key": "k",
                        "subscription_push_enabled": False,
                    }
                }
            ),
            encoding="utf-8",
        )
        self.assertFalse(read_subscription_push_enabled(cfg_path))
        tmp.cleanup()

    @patch("youzi_v2.services.wecom_subscription_push.send_wecom_text")
    def test_try_push_calls_send(self, mock_send) -> None:
        mock_send.return_value = {"ok": True}
        tmp = tempfile.TemporaryDirectory()
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps({"wecom_webhook": {"enabled": True, "key": "k"}}),
            encoding="utf-8",
        )
        with patch(
            "youzi_v2.services.wecom_subscription_push._DEFAULT_CONFIG_PATH",
            cfg_path,
        ):
            try_push_subscription_notification(
                {
                    "shipmentNo": "SH1",
                    "trackingSource": "carrier",
                    "latestTime": "t",
                    "latestDesc": "d",
                },
                config_path=cfg_path,
            )
        mock_send.assert_called_once()
        self.assertIn("承运商轨迹", mock_send.call_args[0][1])
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
