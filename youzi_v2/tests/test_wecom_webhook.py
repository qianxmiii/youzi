"""企业微信通知配置与发送。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from youzi_v2.services.wecom_webhook import (
    load_wecom_webhook_config,
    redact_webhook_url,
    resolve_wecom_mode,
    send_wecom_text,
)


class WecomWebhookConfigTest(unittest.TestCase):
    def test_load_from_key(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "wecom_webhook": {
                        "enabled": True,
                        "key": "test-key-abc",
                    }
                }
            ),
            encoding="utf-8",
        )
        cfg = load_wecom_webhook_config(cfg_path)
        self.assertEqual(cfg["mode"], "webhook")
        self.assertTrue(cfg["enabled"])
        self.assertIn("key=test-key-abc", cfg["send_url"])
        tmp.cleanup()

    def test_aibot_mode_auto_enabled(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "wecom_webhook": {
                        "bot_id": "bot1",
                        "secret": "sec1",
                        "chat_id": "chat_group_1",
                    }
                }
            ),
            encoding="utf-8",
        )
        cfg = load_wecom_webhook_config(cfg_path)
        self.assertEqual(cfg["mode"], "aibot")
        self.assertTrue(cfg["enabled"])
        self.assertEqual(cfg["bot_id"], "bot1")
        self.assertEqual(cfg["chat_id"], "chat_group_1")
        tmp.cleanup()

    def test_resolve_mode(self) -> None:
        self.assertEqual(
            resolve_wecom_mode({"bot_id": "b", "secret": "s"}),
            "aibot",
        )
        self.assertEqual(resolve_wecom_mode({"key": "k"}), "webhook")
        self.assertEqual(resolve_wecom_mode({}), "none")

    def test_redact_key(self) -> None:
        url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=secret123"
        redacted = redact_webhook_url(url)
        self.assertNotIn("secret123", redacted)
        self.assertIn("key=", redacted)


class WecomWebhookSendTest(unittest.TestCase):
    @patch("youzi_v2.services.wecom_webhook.requests.post")
    def test_send_webhook_ok(self, mock_post: MagicMock) -> None:
        tmp = tempfile.TemporaryDirectory()
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps({"wecom_webhook": {"enabled": True, "key": "k1"}}),
            encoding="utf-8",
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_post.return_value = mock_resp

        result = send_wecom_text(cfg_path, "hello")
        self.assertTrue(result["ok"])
        self.assertEqual(result["errcode"], 0)
        tmp.cleanup()

    @patch(
        "youzi_v2.services.wecom_aibot_runtime.read_wecom_long_connection_enabled",
        return_value=False,
    )
    @patch("youzi_v2.services.wecom_aibot_runtime.get_wecom_aibot_runtime", return_value=None)
    @patch("youzi_v2.services.wecom_webhook.send_text_via_session")
    def test_send_aibot_ok(
        self,
        mock_send: MagicMock,
        _mock_runtime: MagicMock,
        _mock_long_conn: MagicMock,
    ) -> None:
        tmp = tempfile.TemporaryDirectory()
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "wecom_webhook": {
                        "bot_id": "b",
                        "secret": "s",
                        "chat_id": "c1",
                    }
                }
            ),
            encoding="utf-8",
        )
        mock_send.return_value = {"ok": True, "errcode": 0, "errmsg": "ok"}
        result = send_wecom_text(cfg_path, "hello")
        self.assertTrue(result["ok"])
        mock_send.assert_called_once()
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
