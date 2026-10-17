"""企业微信智能机器人长连接守护：心跳、回调日志（chat_id）、主动推送。"""

from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import websocket

from .wecom_aibot_log import append_wecom_aibot_log
from .wecom_aibot_shipment_query import (
    build_shipment_query_reply,
    extract_callback_text,
)
from .wecom_aibot_ws import (
    DEFAULT_ACK_TIMEOUT,
    DEFAULT_AUTH_TIMEOUT,
    DEFAULT_WS_URL,
    build_stream_reply_body,
    generate_req_id,
    subscribe,
)
from .wecom_webhook import load_wecom_webhook_config

HEARTBEAT_INTERVAL_SEC = 30.0
RECONNECT_CAP_SEC = 30.0
RECV_TIMEOUT_SEC = 1.0

_RUNTIME: WecomAibotRuntime | None = None
_RUNTIME_LOCK = threading.Lock()


def extract_chat_id_from_frame(frame: dict[str, Any]) -> tuple[str | None, str | None]:
    body = frame.get("body") if isinstance(frame.get("body"), dict) else {}
    chat_id = body.get("chatid") or body.get("chat_id")
    chat_type = body.get("chattype") or body.get("chat_type")
    if chat_id is not None:
        chat_id = str(chat_id).strip() or None
    if chat_type is not None:
        chat_type = str(chat_type).strip() or None
    return chat_id, chat_type


def should_log_chat_callback(cmd: str | None) -> bool:
    return cmd in ("aibot_msg_callback", "aibot_event_callback")


@dataclass
class _PendingAck:
    event: threading.Event
    ack: dict[str, Any] | None = None


@dataclass
class _SendJob:
    chat_id: str
    content: str
    chat_type: int
    done: threading.Event
    result: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class _ReplyJob:
    inbound_req_id: str
    body: dict[str, Any]


class WecomAibotRuntime:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._authenticated = False
        self._ws: websocket.WebSocket | None = None
        self._ws_lock = threading.Lock()
        self._send_queue: queue.Queue[_SendJob | None] = queue.Queue()
        self._reply_queue: queue.Queue[_ReplyJob] = queue.Queue()
        self._pending: dict[str, _PendingAck] = {}
        self._pending_lock = threading.Lock()
        self._seen_msgids: set[str] = set()
        self._msgid_lock = threading.Lock()

    @property
    def is_ready(self) -> bool:
        return self._authenticated and self._ws is not None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        cfg = load_wecom_webhook_config(self._config_path)
        if cfg["mode"] != "aibot" or not cfg["enabled"]:
            return
        if not cfg["bot_id"] or not cfg["secret"]:
            return
        if not read_wecom_long_connection_enabled(self._config_path):
            append_wecom_aibot_log("长连接未启动：wecom_webhook.long_connection=false")
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="wecom-aibot-runtime",
            daemon=True,
        )
        self._thread.start()
        append_wecom_aibot_log("长连接守护线程已启动，等待 WebSocket 认证…")

    def stop(self) -> None:
        self._stop.set()
        self._send_queue.put(None)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        self._close_ws()
        append_wecom_aibot_log("长连接守护已停止")

    def send_text(self, *, chat_id: str, content: str, chat_type: int) -> dict[str, Any]:
        if not self.is_ready:
            raise RuntimeError("智能机器人长连接尚未就绪，请稍后再试或查看 logs/wecom-aibot-*.log")
        job = _SendJob(chat_id=chat_id, content=content, chat_type=chat_type, done=threading.Event())
        self._send_queue.put(job)
        if not job.done.wait(timeout=DEFAULT_ACK_TIMEOUT + 5):
            return {"ok": False, "errcode": -1, "errmsg": "发送超时"}
        if job.error:
            return {"ok": False, "errcode": -1, "errmsg": job.error}
        return job.result or {"ok": False, "errcode": -1, "errmsg": "无响应"}

    def _run_loop(self) -> None:
        delay = 1.0
        while not self._stop.is_set():
            cfg = load_wecom_webhook_config(self._config_path)
            if cfg["mode"] != "aibot" or not cfg["enabled"]:
                break
            try:
                self._connect_session(cfg)
                delay = 1.0
            except Exception as exc:
                self._authenticated = False
                append_wecom_aibot_log(f"长连接异常，{delay:.0f}s 后重连: {exc}")
                if self._stop.wait(delay):
                    break
                delay = min(delay * 2, RECONNECT_CAP_SEC)

    def _connect_session(self, cfg: dict[str, Any]) -> None:
        ws_url = cfg["ws_url"] or DEFAULT_WS_URL
        append_wecom_aibot_log(f"正在连接 {ws_url}")
        ws = websocket.create_connection(ws_url, timeout=DEFAULT_AUTH_TIMEOUT)
        with self._ws_lock:
            self._ws = ws
        try:
            subscribe(ws, bot_id=cfg["bot_id"], secret=cfg["secret"])
            self._authenticated = True
            append_wecom_aibot_log(
                "aibot_subscribe 认证成功；@机器人 发送运单号可查询状态；"
                "chat_id 见 youzi_v2/logs/wecom-aibot-YYYY-MM-DD.log"
            )
            last_ping = time.monotonic()
            while not self._stop.is_set():
                self._drain_reply_queue(ws)
                self._drain_send_queue(ws)
                if time.monotonic() - last_ping >= HEARTBEAT_INTERVAL_SEC:
                    self._send_ping(ws)
                    last_ping = time.monotonic()
                msg = self._recv_json(ws, RECV_TIMEOUT_SEC)
                if msg:
                    self._handle_incoming(msg)
        finally:
            self._authenticated = False
            self._close_ws()

    def _drain_reply_queue(self, ws: websocket.WebSocket) -> None:
        while True:
            try:
                job = self._reply_queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._respond_frame(ws, job.inbound_req_id, job.body)
            except Exception as exc:
                append_wecom_aibot_log(f"回复消息失败 req_id={job.inbound_req_id}: {exc}")

    def _respond_frame(
        self,
        ws: websocket.WebSocket,
        inbound_req_id: str,
        body: dict[str, Any],
    ) -> None:
        self._request_ack(
            ws,
            {
                "cmd": "aibot_respond_msg",
                "headers": {"req_id": inbound_req_id},
                "body": body,
            },
            inbound_req_id,
        )

    def _drain_send_queue(self, ws: websocket.WebSocket) -> None:
        while True:
            try:
                job = self._send_queue.get_nowait()
            except queue.Empty:
                break
            if job is None:
                return
            try:
                job.result = self._send_text_frame(
                    ws,
                    chat_id=job.chat_id,
                    content=job.content,
                    chat_type=job.chat_type,
                )
            except Exception as exc:
                job.error = str(exc)
            finally:
                job.done.set()

    def _send_text_frame(
        self,
        ws: websocket.WebSocket,
        *,
        chat_id: str,
        content: str,
        chat_type: int,
    ) -> dict[str, Any]:
        req_id = generate_req_id("send")
        body: dict[str, Any] = {
            "chatid": chat_id,
            "chat_type": chat_type,
            "msgtype": "text",
            "text": {"content": content},
        }
        ack = self._request_ack(
            ws,
            {
                "cmd": "aibot_send_msg",
                "headers": {"req_id": req_id},
                "body": body,
            },
            req_id,
        )
        errcode = int(ack.get("errcode", -1))
        errmsg = str(ack.get("errmsg") or "")
        return {"ok": errcode == 0, "errcode": errcode, "errmsg": errmsg}

    def _send_ping(self, ws: websocket.WebSocket) -> None:
        req_id = generate_req_id("ping")
        try:
            self._request_ack(
                ws,
                {"cmd": "ping", "headers": {"req_id": req_id}},
                req_id,
                timeout=10.0,
            )
        except TimeoutError:
            append_wecom_aibot_log("心跳 ack 超时")
            raise RuntimeError("心跳 ack 超时") from None

    def _request_ack(
        self,
        ws: websocket.WebSocket,
        frame: dict[str, Any],
        req_id: str,
        *,
        timeout: float = DEFAULT_ACK_TIMEOUT,
    ) -> dict[str, Any]:
        pending = _PendingAck(event=threading.Event())
        with self._pending_lock:
            self._pending[req_id] = pending
        try:
            ws.send(json.dumps(frame, ensure_ascii=False))
            # 本方法运行于接收线程，等待期间也必须接收并分发 ACK/回调。
            deadline = time.monotonic() + timeout
            while not pending.event.is_set():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"等待 ack 超时 req_id={req_id}")
                if self._stop.is_set():
                    raise RuntimeError("长连接已停止")
                msg = self._recv_json(ws, min(RECV_TIMEOUT_SEC, remaining))
                if msg:
                    self._handle_incoming(msg)
            if pending.ack is None:
                raise RuntimeError(f"ack 为空 req_id={req_id}")
            errcode = int(pending.ack.get("errcode", -1))
            if errcode != 0:
                errmsg = str(pending.ack.get("errmsg") or "")
                raise RuntimeError(f"errcode={errcode} errmsg={errmsg}")
            return pending.ack
        finally:
            with self._pending_lock:
                self._pending.pop(req_id, None)

    def _recv_json(self, ws: websocket.WebSocket, timeout: float) -> dict[str, Any] | None:
        ws.settimeout(timeout)
        try:
            raw = ws.recv()
        except websocket.WebSocketTimeoutException:
            return None
        except Exception as exc:
            raise RuntimeError(f"接收失败: {exc}") from exc
        if not raw:
            raise RuntimeError("WebSocket 连接已关闭")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None

    def _handle_incoming(self, msg: dict[str, Any]) -> None:
        cmd = msg.get("cmd")
        headers = msg.get("headers") if isinstance(msg.get("headers"), dict) else {}
        req_id = headers.get("req_id")
        if req_id and "errcode" in msg:
            with self._pending_lock:
                slot = self._pending.get(req_id)
                if slot is not None:
                    slot.ack = msg
                    slot.event.set()

        if cmd == "aibot_msg_callback":
            self._enqueue_shipment_query_reply(msg)

        if should_log_chat_callback(str(cmd) if cmd else None):
            chat_id, chat_type = extract_chat_id_from_frame(msg)
            if chat_id:
                append_wecom_aibot_log(
                    f"发现 chat_id={chat_id} chat_type={chat_type or '?'} cmd={cmd} "
                    "→ 写入 config.json wecom_webhook.chat_id"
                )
            else:
                append_wecom_aibot_log(f"收到回调 cmd={cmd}（帧内无 chatid）")

    def _should_process_msgid(self, msgid: str) -> bool:
        key = msgid.strip()
        if not key:
            return True
        with self._msgid_lock:
            if key in self._seen_msgids:
                return False
            self._seen_msgids.add(key)
            if len(self._seen_msgids) > 500:
                self._seen_msgids = set(list(self._seen_msgids)[-300:])
            return True

    def _enqueue_shipment_query_reply(self, msg: dict[str, Any]) -> None:
        if not read_wecom_shipment_query_enabled(self._config_path):
            return
        body = msg.get("body") if isinstance(msg.get("body"), dict) else {}
        msgid = str(body.get("msgid") or "")
        if not self._should_process_msgid(msgid):
            return
        headers = msg.get("headers") if isinstance(msg.get("headers"), dict) else {}
        inbound_req_id = (headers.get("req_id") or "").strip()
        text = extract_callback_text(msg)
        if not inbound_req_id or not text:
            return
        append_wecom_aibot_log(f"收到查单消息，解析运单号…")
        threading.Thread(
            target=self._build_and_queue_reply,
            args=(inbound_req_id, text),
            daemon=True,
            name="wecom-aibot-shipment-query",
        ).start()

    def _build_and_queue_reply(self, inbound_req_id: str, text: str) -> None:
        try:
            content = build_shipment_query_reply(text)
        except Exception as exc:
            content = f"查询失败：{exc}"
            append_wecom_aibot_log(f"运单查询异常: {exc}")
        self._reply_queue.put(
            _ReplyJob(
                inbound_req_id=inbound_req_id,
                body=build_stream_reply_body(content),
            )
        )

    def _close_ws(self) -> None:
        with self._ws_lock:
            if self._ws is not None:
                try:
                    self._ws.close()
                except Exception:
                    pass
                self._ws = None


def read_wecom_shipment_query_enabled(config_path: Path) -> bool:
    if not config_path.is_file():
        return True
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    block = data.get("wecom_webhook") if isinstance(data.get("wecom_webhook"), dict) else {}
    raw = block.get("shipment_query_enabled")
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def read_wecom_long_connection_enabled(config_path: Path) -> bool:
    if not config_path.is_file():
        return True
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    block = data.get("wecom_webhook") if isinstance(data.get("wecom_webhook"), dict) else {}
    raw = block.get("long_connection")
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def start_wecom_aibot_runtime(config_path: Path) -> None:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = WecomAibotRuntime(config_path)
        _RUNTIME.start()


def stop_wecom_aibot_runtime() -> None:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is not None:
            _RUNTIME.stop()


def get_wecom_aibot_runtime() -> WecomAibotRuntime | None:
    return _RUNTIME
