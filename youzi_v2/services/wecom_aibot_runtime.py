"""企业微信智能机器人长连接守护：心跳、回调日志（chat_id）、主动推送。"""

from __future__ import annotations

import base64
import hashlib
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
    build_wecom_cargo_file,
    build_wecom_mark_file,
    build_wecom_mark_split_files,
    build_wecom_packinglist_file,
    build_wecom_warehouse_entry_file,
    build_wecom_warehouse_entry_pdf_file,
    extract_callback_text,
    message_wants_cargo_download,
    message_wants_mark_download,
    message_wants_mark_split,
    message_wants_packinglist_download,
    message_wants_warehouse_entry_download,
    message_wants_warehouse_entry_pdf,
)
from .wecom_aibot_ws import (
    DEFAULT_ACK_TIMEOUT,
    DEFAULT_AUTH_TIMEOUT,
    DEFAULT_WS_URL,
    build_markdown_reply_body,
    build_stream_reply_body,
    generate_req_id,
    subscribe,
)
from .wecom_webhook import load_wecom_webhook_config

HEARTBEAT_INTERVAL_SEC = 30.0
RECONNECT_CAP_SEC = 30.0
RECV_TIMEOUT_SEC = 1.0
_MEDIA_CHUNK_BYTES = 512 * 1024
_MEDIA_FILE_MAX_BYTES = 20 * 1024 * 1024
_MEDIA_FILE_MIN_BYTES = 5

_RUNTIME: WecomAibotRuntime | None = None
_RUNTIME_LOCK = threading.Lock()


def extract_sender_userid(frame: dict[str, Any]) -> str | None:
    body = frame.get("body") if isinstance(frame.get("body"), dict) else {}
    sender = body.get("from") if isinstance(body.get("from"), dict) else {}
    raw = sender.get("userid") or body.get("fromuserid")
    if isinstance(raw, dict):
        raw = raw.get("userid")
    userid = str(raw or "").strip()
    return userid or None


def mention_prefix(userid: str | None, chat_type: str | None) -> str:
    """智能机器人回复气泡不渲染 <@userid>，写入正文只会显示原文。暂不 @。"""
    del userid, chat_type
    return ""


def extract_chat_id_from_frame(frame: dict[str, Any]) -> tuple[str | None, str | None]:
    body = frame.get("body") if isinstance(frame.get("body"), dict) else {}
    chat_id = body.get("chatid") or body.get("chat_id")
    chat_type = body.get("chattype") or body.get("chat_type")
    if chat_id is not None:
        chat_id = str(chat_id).strip() or None
    if chat_type is not None:
        chat_type = str(chat_type).strip() or None
    return chat_id, chat_type


def resolve_reply_chat(
    chat_id: str | None,
    chat_type: str | None,
    sender_userid: str | None,
) -> tuple[str | None, str]:
    """群聊用回调里的 chatid。单聊不返回 chatid，主动发送时改用发送者 userid。"""
    kind = (chat_type or "").strip().lower()
    if chat_id:
        if kind in ("1", "single"):
            return chat_id, "1"
        return chat_id, "2"
    if sender_userid:
        return sender_userid, "1"
    return None, "2"


def should_log_chat_callback(cmd: str | None) -> bool:
    return cmd in ("aibot_msg_callback", "aibot_event_callback")


def _ack_body(ack: dict[str, Any]) -> dict[str, Any]:
    body = ack.get("body")
    return body if isinstance(body, dict) else {}


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
    markdown: bool = False
    result: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class _ReplyJob:
    inbound_req_id: str
    body: dict[str, Any]


@dataclass
class _FileJob:
    inbound_req_id: str
    chat_id: str
    chat_type: int
    filename: str
    content: bytes
    done: threading.Event
    error: str | None = None
    responded: bool = False
    respond: bool = True


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
        self._file_queue: queue.Queue[_FileJob] = queue.Queue()
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

    def send_text(
        self,
        *,
        chat_id: str,
        content: str,
        chat_type: int,
        markdown: bool = False,
    ) -> dict[str, Any]:
        if not self.is_ready:
            raise RuntimeError("智能机器人长连接尚未就绪，请稍后再试或查看 logs/wecom-aibot-*.log")
        job = _SendJob(
            chat_id=chat_id,
            content=content,
            chat_type=chat_type,
            done=threading.Event(),
            markdown=markdown,
        )
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
                self._drain_file_queue(ws)
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

    def _drain_file_queue(self, ws: websocket.WebSocket) -> None:
        while True:
            try:
                job = self._file_queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._upload_and_send_file(ws, job)
            except Exception as exc:
                job.error = str(exc)
                append_wecom_aibot_log(f"发送文件失败 {job.filename}: {exc}")
            finally:
                job.done.set()

    def _upload_and_send_file(self, ws: websocket.WebSocket, job: _FileJob) -> None:
        content = job.content
        size = len(content)
        if size < _MEDIA_FILE_MIN_BYTES:
            raise RuntimeError("文件过小，无法上传")
        if size > _MEDIA_FILE_MAX_BYTES:
            raise RuntimeError("文件超过 20MB，企业微信不接收")
        chunk_size = _MEDIA_CHUNK_BYTES
        total_chunks = max(1, (size + chunk_size - 1) // chunk_size)
        if total_chunks > 100:
            raise RuntimeError("文件分片过多，无法上传")
        md5 = hashlib.md5(content).hexdigest()
        init_id = generate_req_id("upinit")
        init_ack = self._request_ack(
            ws,
            {
                "cmd": "aibot_upload_media_init",
                "headers": {"req_id": init_id},
                "body": {
                    "type": "file",
                    "filename": job.filename,
                    "total_size": size,
                    "total_chunks": total_chunks,
                    "md5": md5,
                },
            },
            init_id,
            timeout=30.0,
        )
        upload_id = _ack_body(init_ack).get("upload_id")
        if not upload_id:
            raise RuntimeError("上传初始化未返回 upload_id")
        for index in range(total_chunks):
            start = index * chunk_size
            piece = content[start : start + chunk_size]
            chunk_id = generate_req_id("upchunk")
            self._request_ack(
                ws,
                {
                    "cmd": "aibot_upload_media_chunk",
                    "headers": {"req_id": chunk_id},
                    "body": {
                        "upload_id": upload_id,
                        "chunk_index": index,
                        "base64_data": base64.b64encode(piece).decode("ascii"),
                    },
                },
                chunk_id,
                timeout=30.0,
            )
        finish_id = generate_req_id("updone")
        finish_ack = self._request_ack(
            ws,
            {
                "cmd": "aibot_upload_media_finish",
                "headers": {"req_id": finish_id},
                "body": {"upload_id": upload_id},
            },
            finish_id,
            timeout=30.0,
        )
        media_id = str(_ack_body(finish_ack).get("media_id") or "").strip()
        if not media_id:
            raise RuntimeError("上传完成未返回 media_id")
        file_body = {"msgtype": "file", "file": {"media_id": media_id}}
        if job.respond:
            try:
                self._respond_frame(ws, job.inbound_req_id, file_body)
            except Exception as exc:
                if not job.chat_id:
                    raise
                append_wecom_aibot_log(f"被动回复文件失败，改为主动发送: {exc}")
                self._send_file_message(ws, job, media_id)
        else:
            self._send_file_message(ws, job, media_id)
        job.responded = True
        append_wecom_aibot_log(f"已回复文件 {job.filename}，{size} 字节")

    def _send_file_message(
        self,
        ws: websocket.WebSocket,
        job: _FileJob,
        media_id: str,
    ) -> None:
        if not job.chat_id:
            raise RuntimeError("当前会话缺少 chat_id，无法继续发送文件")
        send_id = generate_req_id("sendfile")
        self._request_ack(
            ws,
            {
                "cmd": "aibot_send_msg",
                "headers": {"req_id": send_id},
                "body": {
                    "chatid": job.chat_id,
                    "chat_type": job.chat_type,
                    "msgtype": "file",
                    "file": {"media_id": media_id},
                },
            },
            send_id,
            timeout=30.0,
        )

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
                    markdown=job.markdown,
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
        markdown: bool = False,
    ) -> dict[str, Any]:
        req_id = generate_req_id("send")
        if markdown:
            payload: dict[str, Any] = {
                "chatid": chat_id,
                "chat_type": chat_type,
                "msgtype": "markdown",
                "markdown": {"content": content},
            }
        else:
            payload = {
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
                "body": payload,
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
            elif extract_sender_userid(msg):
                append_wecom_aibot_log(
                    f"收到回调 cmd={cmd}（单聊无 chatid，后续文件按发送者 userid 发送）"
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
        body = msg.get("body") if isinstance(msg.get("body"), dict) else {}
        msgtype = str(body.get("msgtype") or "").strip() or "?"
        if not read_wecom_shipment_query_enabled(self._config_path):
            append_wecom_aibot_log("收到 aibot_msg_callback，但 shipment_query_enabled=false，跳过")
            return
        msgid = str(body.get("msgid") or "")
        if not self._should_process_msgid(msgid):
            append_wecom_aibot_log(f"收到 aibot_msg_callback，重复 msgid 已忽略 msgtype={msgtype}")
            return
        headers = msg.get("headers") if isinstance(msg.get("headers"), dict) else {}
        inbound_req_id = (headers.get("req_id") or "").strip()
        text = extract_callback_text(msg)
        if not inbound_req_id:
            append_wecom_aibot_log(f"收到 aibot_msg_callback，但缺少 headers.req_id，无法回复 msgtype={msgtype}")
            return
        if not text:
            if body.get("compat_info"):
                append_wecom_aibot_log("收到 aibot_msg_callback，compat_info 兼容帧，跳过")
            else:
                append_wecom_aibot_log(
                    f"收到 aibot_msg_callback，无法解析文本（仅支持 text/mixed）msgtype={msgtype}"
                )
            return
        preview = text.replace("\n", " ")[:80]
        append_wecom_aibot_log(f"收到查单消息 msgtype={msgtype}：{preview}")
        chat_id, chat_type = extract_chat_id_from_frame(msg)
        sender_userid = extract_sender_userid(msg)
        chat_id, chat_type = resolve_reply_chat(chat_id, chat_type, sender_userid)
        threading.Thread(
            target=self._build_and_queue_reply,
            args=(inbound_req_id, text, chat_id, chat_type, sender_userid),
            daemon=True,
            name="wecom-aibot-shipment-query",
        ).start()

    def _with_mention(self, content: str, userid: str | None, chat_type: str | None) -> str:
        prefix = mention_prefix(userid, chat_type)
        if not prefix:
            return content
        return prefix + content

    def _queue_text_reply(
        self,
        inbound_req_id: str,
        content: str,
        *,
        userid: str | None = None,
        chat_type: str | None = None,
    ) -> None:
        mentioned = self._with_mention(content, userid, chat_type)
        if mentioned != content:
            body = build_markdown_reply_body(mentioned)
        else:
            body = build_stream_reply_body(content)
        self._reply_queue.put(
            _ReplyJob(
                inbound_req_id=inbound_req_id,
                body=body,
            )
        )

    def _send_followup_text(
        self,
        chat_id: str | None,
        chat_type: str | None,
        content: str,
        *,
        userid: str | None = None,
    ) -> None:
        if not chat_id or not content.strip():
            return
        try:
            parsed = int(chat_type) if chat_type else 2
        except (TypeError, ValueError):
            parsed = 2
        mentioned = self._with_mention(content, userid, chat_type)
        try:
            self.send_text(
                chat_id=chat_id,
                content=mentioned,
                chat_type=parsed,
                markdown=mentioned != content,
            )
        except Exception as exc:
            append_wecom_aibot_log(f"补充文字发送失败: {exc}")

    def _deliver_download_file(
        self,
        inbound_req_id: str,
        text: str,
        chat_id: str | None,
        chat_type: str | None,
        sender_userid: str | None,
        builder,
        label: str,
    ) -> None:
        try:
            content, filename, note = builder(text)
        except Exception as exc:
            append_wecom_aibot_log(f"{label}生成失败: {exc}")
            self._queue_text_reply(
                inbound_req_id,
                f"{label}未发出：{exc}",
                userid=sender_userid,
                chat_type=chat_type,
            )
            return
        try:
            parsed_type = int(chat_type) if chat_type else 2
        except (TypeError, ValueError):
            parsed_type = 2
        job = _FileJob(
            inbound_req_id=inbound_req_id,
            chat_id=chat_id or "",
            chat_type=parsed_type,
            filename=filename,
            content=content,
            done=threading.Event(),
        )
        self._file_queue.put(job)
        if not job.done.wait(timeout=180):
            append_wecom_aibot_log(f"发送文件超时 {filename}")
            if not job.responded:
                self._queue_text_reply(
                    inbound_req_id,
                    f"{label}文件发送超时，请稍后再试。",
                    userid=sender_userid,
                    chat_type=chat_type,
                )
            return
        if job.error and not job.responded:
            self._queue_text_reply(
                inbound_req_id,
                f"{label}文件发送失败：{job.error}",
                userid=sender_userid,
                chat_type=chat_type,
            )
            return
        if job.error:
            self._send_followup_text(
                chat_id,
                chat_type,
                f"{label}文件发送失败：{job.error}",
                userid=sender_userid,
            )
            return
        if note:
            self._send_followup_text(chat_id, chat_type, note, userid=sender_userid)

    def _files_for_this_chat(
        self,
        files: list[tuple[bytes, str]],
        chat_id: str | None,
    ) -> list[tuple[bytes, str]]:
        """没有会话编号时无法连发，多份改成一个压缩包。"""
        if len(files) <= 1 or chat_id:
            return files
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for content, name in files:
                zf.writestr(name, content)
        return [(buf.getvalue(), f"唛头拆分_{len(files)}份.zip")]

    def _deliver_download_files(
        self,
        inbound_req_id: str,
        text: str,
        chat_id: str | None,
        chat_type: str | None,
        sender_userid: str | None,
        builder,
        label: str,
    ) -> None:
        try:
            files, note = builder(text)
        except Exception as exc:
            append_wecom_aibot_log(f"{label}生成失败: {exc}")
            self._queue_text_reply(
                inbound_req_id,
                f"{label}未发出：{exc}",
                userid=sender_userid,
                chat_type=chat_type,
            )
            return
        files = [(content, name) for content, name in files if content and name]
        if not files:
            self._queue_text_reply(
                inbound_req_id,
                f"{label}未生成文件。",
                userid=sender_userid,
                chat_type=chat_type,
            )
            return
        files = self._files_for_this_chat(files, chat_id)
        try:
            parsed_type = int(chat_type) if chat_type else 2
        except (TypeError, ValueError):
            parsed_type = 2
        sent = 0
        for index, (content, filename) in enumerate(files):
            job = _FileJob(
                inbound_req_id=inbound_req_id,
                chat_id=chat_id or "",
                chat_type=parsed_type,
                filename=filename,
                content=content,
                done=threading.Event(),
                respond=index == 0,
            )
            self._file_queue.put(job)
            if not job.done.wait(timeout=180):
                detail = f"{label}文件发送超时，请稍后再试。"
                self._report_partial_file_failure(
                    inbound_req_id,
                    chat_id,
                    chat_type,
                    sender_userid,
                    detail,
                    sent=sent,
                    replied=job.responded,
                )
                return
            if job.error:
                detail = f"{label}文件发送失败：{job.error}"
                self._report_partial_file_failure(
                    inbound_req_id,
                    chat_id,
                    chat_type,
                    sender_userid,
                    detail,
                    sent=sent,
                    replied=job.responded,
                )
                return
            sent += 1
        if note:
            self._send_followup_text(chat_id, chat_type, note, userid=sender_userid)

    def _report_partial_file_failure(
        self,
        inbound_req_id: str,
        chat_id: str | None,
        chat_type: str | None,
        sender_userid: str | None,
        detail: str,
        *,
        sent: int,
        replied: bool,
    ) -> None:
        message = f"已发出 {sent} 份。{detail}" if sent else detail
        if sent or replied:
            self._send_followup_text(
                chat_id,
                chat_type,
                message,
                userid=sender_userid,
            )
            return
        self._queue_text_reply(
            inbound_req_id,
            message,
            userid=sender_userid,
            chat_type=chat_type,
        )

    def _build_and_queue_reply(
        self,
        inbound_req_id: str,
        text: str,
        chat_id: str | None = None,
        chat_type: str | None = None,
        sender_userid: str | None = None,
    ) -> None:
        if message_wants_packinglist_download(text):
            self._deliver_download_file(
                inbound_req_id,
                text,
                chat_id,
                chat_type,
                sender_userid,
                build_wecom_packinglist_file,
                "箱单发票",
            )
            return
        if message_wants_warehouse_entry_download(text):
            pdf = message_wants_warehouse_entry_pdf(text)
            self._deliver_download_file(
                inbound_req_id,
                text,
                chat_id,
                chat_type,
                sender_userid,
                build_wecom_warehouse_entry_pdf_file
                if pdf
                else build_wecom_warehouse_entry_file,
                "进仓单",
            )
            return
        if message_wants_mark_split(text):
            self._deliver_download_files(
                inbound_req_id,
                text,
                chat_id,
                chat_type,
                sender_userid,
                build_wecom_mark_split_files,
                "唛头拆分",
            )
            return
        if message_wants_mark_download(text):
            self._deliver_download_file(
                inbound_req_id,
                text,
                chat_id,
                chat_type,
                sender_userid,
                build_wecom_mark_file,
                "唛头",
            )
            return
        if message_wants_cargo_download(text):
            self._deliver_download_file(
                inbound_req_id,
                text,
                chat_id,
                chat_type,
                sender_userid,
                build_wecom_cargo_file,
                "货箱",
            )
            return
        try:
            content = build_shipment_query_reply(text)
            append_wecom_aibot_log(f"查单回复已入队，长度={len(content)}")
        except Exception as exc:
            content = f"查询失败：{exc}"
            append_wecom_aibot_log(f"运单查询异常: {exc}")
        self._queue_text_reply(
            inbound_req_id,
            content,
            userid=sender_userid,
            chat_type=chat_type,
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
