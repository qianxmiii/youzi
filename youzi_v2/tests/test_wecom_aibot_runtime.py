"""企业微信智能机器人 chat_id 解析。"""

from __future__ import annotations

import unittest

from youzi_v2.services.wecom_aibot_runtime import extract_chat_id_from_frame


class WecomAibotRuntimeTest(unittest.TestCase):
    def test_extract_chat_id(self) -> None:
        frame = {
            "cmd": "aibot_msg_callback",
            "body": {"chatid": "wrABC123", "chattype": "group"},
        }
        chat_id, chat_type = extract_chat_id_from_frame(frame)
        self.assertEqual(chat_id, "wrABC123")
        self.assertEqual(chat_type, "group")


if __name__ == "__main__":
    unittest.main()
