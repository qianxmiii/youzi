"""独立运行的企微客户群收发验证，只回复固定测试指令。"""
from __future__ import annotations

import argparse
import re
import threading
from pathlib import Path
from typing import Any

from .wecom_aibot_log import append_wecom_aibot_log
from .wecom_aibot_runtime import WecomAibotRuntime, extract_chat_id_from_frame, extract_callback_text, extract_sender_userid
from .wecom_aibot_ws import DEFAULT_WS_URL
from .wecom_webhook import _read_config_file

_PROBE = re.compile(r"(?:@[^\r\n]+?\s+)?查轨迹\s+TEST-001", re.IGNORECASE)
_REPLY = "客户群查轨迹测试成功（TEST-001）。这是一条测试回复。"


def load_pilot_config(config_path: Path) -> dict[str, Any]:
    config = _read_config_file(config_path)
    public = config.get("wecom_webhook_public")
    if not isinstance(public, dict):
        raise ValueError("缺少 wecom_webhook_public 配置")
    bot_id = str(public.get("bot_id") or public.get("botId") or "").strip()
    secret = str(public.get("secret") or "").strip()
    if not bot_id or not secret:
        raise ValueError("wecom_webhook_public 缺少 Bot ID 或 Secret")
    internal = config.get("wecom_webhook")
    if isinstance(internal, dict):
        internal_id = str(internal.get("bot_id") or internal.get("botId") or "").strip()
        if internal_id == bot_id:
            raise ValueError("客户群试点必须使用独立的 Bot ID")
    if public.get("enabled") is False or public.get("long_connection") is False:
        raise ValueError("客户群机器人长连接已停用")
    return {
        "mode": "aibot", "enabled": True, "ws_url": DEFAULT_WS_URL,
        "bot_id": bot_id, "secret": secret,
        "chat_id": str(public.get("chat_id") or "").strip(),
    }


class PublicGroupPilot(WecomAibotRuntime):
    def __init__(self, config_path: Path) -> None:
        super().__init__(config_path)
        self._pilot_config = load_pilot_config(config_path)
        self.replied = threading.Event()
        self._matched_group: str | None = None
        self._reply_pending = False

    def _load_connection_config(self) -> dict[str, Any]:
        return self._pilot_config

    def _long_connection_enabled(self) -> bool:
        return True

    def _on_authenticated(self) -> None:
        append_wecom_aibot_log("[客户群试点] Bot 已认证，等待客户群测试指令")

    def _handle_callback(self, cmd: str, msg: dict[str, Any]) -> None:
        if cmd != "aibot_msg_callback" or self._reply_pending or self.replied.is_set():
            return
        chat_id, chat_type = extract_chat_id_from_frame(msg)
        if not chat_id or (chat_type or "").lower() not in {"group", "2"}:
            return
        allowed_group = self._pilot_config["chat_id"] or self._matched_group
        if allowed_group and allowed_group != chat_id:
            return
        sender = extract_sender_userid(msg)
        headers = msg.get("headers")
        req_id = headers.get("req_id") if isinstance(headers, dict) else None
        text = extract_callback_text(msg)
        if not sender or not isinstance(req_id, str) or not req_id.strip() or not text or not _PROBE.fullmatch(text):
            return
        body = msg["body"]
        if not self._should_process_msgid(str(body.get("msgid") or req_id)):
            return
        self._matched_group = chat_id
        self._reply_pending = True
        append_wecom_aibot_log("[客户群试点] 收到群消息正文、群 ID 和发送人标识，准备回复原消息")
        self._queue_text_reply(req_id, _REPLY)

    def _respond_frame(self, ws, inbound_req_id: str, body: dict[str, Any]) -> None:
        try:
            super()._respond_frame(ws, inbound_req_id, body)
            append_wecom_aibot_log("[客户群试点] 企微已确认接收同群回复")
            self.replied.set()
        finally:
            self._reply_pending = False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/config.json"))
    parser.add_argument("--seconds", type=int, default=900)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds 必须大于零")
    try:
        pilot = PublicGroupPilot(args.config)
    except ValueError as exc:
        parser.error(str(exc))
    pilot.start()
    try:
        if pilot.replied.wait(args.seconds):
            return 0
        append_wecom_aibot_log("[客户群试点] 验证窗口结束，未取得同群回复确认")
        return 1
    finally:
        pilot.stop()


if __name__ == "__main__":
    raise SystemExit(main())
