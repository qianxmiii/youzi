"""企业微信智能机器人长连接（WebSocket）帧与单次会话发送。

协议：https://developer.work.weixin.qq.com/document/path/101463
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import websocket

DEFAULT_WS_URL = "wss://openws.work.weixin.qq.com"
DEFAULT_AUTH_TIMEOUT = 15.0
DEFAULT_ACK_TIMEOUT = 15.0


def generate_req_id(prefix: str = "youzi") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _send_frame(ws: websocket.WebSocket, frame: dict[str, Any]) -> None:
    ws.send(json.dumps(frame, ensure_ascii=False))


def _recv_json(ws: websocket.WebSocket, timeout: float) -> dict[str, Any] | None:
    ws.settimeout(timeout)
    try:
        raw = ws.recv()
    except websocket.WebSocketTimeoutException:
        return None
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    return data if isinstance(data, dict) else None


def _wait_ack(ws: websocket.WebSocket, req_id: str, *, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remain = max(0.1, deadline - time.monotonic())
        msg = _recv_json(ws, remain)
        if not msg:
            continue
        headers = msg.get("headers") if isinstance(msg.get("headers"), dict) else {}
        if headers.get("req_id") == req_id:
            return msg
        # 推送回调（如 aibot_msg_callback）在单次发送场景可忽略
    raise TimeoutError(f"等待 ack 超时 req_id={req_id}")


def subscribe(ws: websocket.WebSocket, *, bot_id: str, secret: str) -> dict[str, Any]:
    req_id = generate_req_id("sub")
    _send_frame(
        ws,
        {
            "cmd": "aibot_subscribe",
            "headers": {"req_id": req_id},
            "body": {"bot_id": bot_id, "secret": secret},
        },
    )
    ack = _wait_ack(ws, req_id, timeout=DEFAULT_AUTH_TIMEOUT)
    errcode = int(ack.get("errcode", -1))
    if errcode != 0:
        errmsg = str(ack.get("errmsg") or "")
        raise RuntimeError(f"aibot_subscribe 失败 errcode={errcode} errmsg={errmsg}")
    return ack


def send_text_message(
    ws: websocket.WebSocket,
    *,
    chat_id: str,
    content: str,
    chat_type: int = 2,
) -> dict[str, Any]:
    req_id = generate_req_id("send")
    body: dict[str, Any] = {
        "chatid": chat_id,
        "chat_type": chat_type,
        "msgtype": "text",
        "text": {"content": content},
    }
    _send_frame(
        ws,
        {
            "cmd": "aibot_send_msg",
            "headers": {"req_id": req_id},
            "body": body,
        },
    )
    ack = _wait_ack(ws, req_id, timeout=DEFAULT_ACK_TIMEOUT)
    errcode = int(ack.get("errcode", -1))
    errmsg = str(ack.get("errmsg") or "")
    return {"ok": errcode == 0, "errcode": errcode, "errmsg": errmsg}


def build_stream_reply_body(content: str, *, stream_id: str | None = None) -> dict[str, Any]:
    """被动回复须用 stream（finish=true 一次性回复）。"""
    sid = stream_id or generate_req_id("stream")
    return {
        "msgtype": "stream",
        "stream": {
            "id": sid,
            "finish": True,
            "content": content,
        },
    }


def send_text_via_session(
    *,
    ws_url: str,
    bot_id: str,
    secret: str,
    chat_id: str,
    content: str,
    chat_type: int = 2,
) -> dict[str, Any]:
    """建立连接 → 认证 → 主动推送 → 关闭（适合低频通知；同 bot 勿并发多连接）。"""
    ws = websocket.create_connection(ws_url, timeout=DEFAULT_AUTH_TIMEOUT)
    try:
        subscribe(ws, bot_id=bot_id, secret=secret)
        return send_text_message(
            ws,
            chat_id=chat_id,
            content=content,
            chat_type=chat_type,
        )
    finally:
        try:
            ws.close()
        except Exception:
            pass
