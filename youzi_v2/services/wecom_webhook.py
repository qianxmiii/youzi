"""企业微信通知：Webhook 消息推送 或 智能机器人长连接（bot_id + secret）。

密钥与 bot 凭证仅 config.json → wecom_webhook。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from .wecom_aibot_ws import DEFAULT_WS_URL, send_text_via_session

CONFIG_KEY = "wecom_webhook"
DEFAULT_SEND_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
DEFAULT_TIMEOUT = 15

WecomMode = Literal["webhook", "aibot", "none"]


def _read_block(config: dict[str, Any]) -> dict[str, Any]:
    block = config.get(CONFIG_KEY)
    return block if isinstance(block, dict) else {}


def _read_config_file(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def resolve_wecom_mode(block: dict[str, Any]) -> WecomMode:
    bot_id = (block.get("bot_id") or block.get("botId") or "").strip()
    secret = (block.get("secret") or "").strip()
    if bot_id and secret:
        return "aibot"
    if (block.get("url") or "").strip() or (block.get("key") or "").strip():
        return "webhook"
    return "none"


def load_wecom_webhook_config(config_path: Path) -> dict[str, Any]:
    """读取 wecom 配置；返回 mode、enabled、发送所需字段。"""
    block = _read_block(_read_config_file(config_path))
    mode = resolve_wecom_mode(block)
    timeout = int(block.get("timeout") or DEFAULT_TIMEOUT)
    timeout = max(5, min(timeout, 60))

    explicit_enabled = block.get("enabled")
    if explicit_enabled is None:
        enabled = mode != "none"
    else:
        enabled = bool(explicit_enabled) and mode != "none"

    cfg: dict[str, Any] = {
        "mode": mode,
        "enabled": enabled,
        "timeout": timeout,
        "send_url": "",
        "bot_id": "",
        "secret": "",
        "ws_url": (block.get("ws_url") or block.get("wsUrl") or DEFAULT_WS_URL).strip(),
        "chat_id": (block.get("chat_id") or block.get("chatid") or block.get("chatId") or "").strip(),
        "chat_type": int(block.get("chat_type") or block.get("chatType") or 2),
    }

    if mode == "webhook":
        cfg["send_url"] = _resolve_send_url(block)
        if not cfg["send_url"]:
            cfg["enabled"] = False
    elif mode == "aibot":
        cfg["bot_id"] = (block.get("bot_id") or block.get("botId") or "").strip()
        cfg["secret"] = (block.get("secret") or "").strip()

    return cfg


def _resolve_send_url(block: dict[str, Any]) -> str:
    raw_url = (block.get("url") or "").strip()
    if raw_url:
        return raw_url
    key = (block.get("key") or "").strip()
    if not key:
        return ""
    return f"{DEFAULT_SEND_URL}?key={key}"


def require_wecom_webhook_config(config_path: Path) -> dict[str, Any]:
    cfg = load_wecom_webhook_config(config_path)
    if not cfg["enabled"]:
        raise ValueError(
            "config.json 未启用 wecom_webhook：请设置 enabled=true，"
            "或配置 bot_id+secret（智能机器人）/ key 或 url（消息推送 Webhook）"
        )
    if cfg["mode"] == "webhook" and not cfg["send_url"]:
        raise ValueError("config.json wecom_webhook 缺少 key 或 url")
    if cfg["mode"] == "aibot":
        if not cfg["bot_id"] or not cfg["secret"]:
            raise ValueError("config.json wecom_webhook 缺少 bot_id 或 secret")
        if not cfg["chat_id"]:
            raise ValueError(
                "智能机器人主动推送需配置 chat_id：在目标群/单聊中先 @机器人 发一条消息，"
                "从 youzi_v2/logs/wecom-aibot-*.log 或回调 body.chatid 获取后写入 config.json"
            )
    return cfg


def send_wecom_text(config_path: Path, content: str) -> dict[str, Any]:
    """发送 text 消息；成功时 ok=True。"""
    text = (content or "").strip()
    if not text:
        raise ValueError("消息内容不能为空")
    cfg = require_wecom_webhook_config(config_path)
    if cfg["mode"] == "aibot":
        from .wecom_aibot_runtime import (
            get_wecom_aibot_runtime,
            read_wecom_long_connection_enabled,
        )

        runtime = get_wecom_aibot_runtime()
        if runtime is not None and runtime.is_ready:
            return runtime.send_text(
                chat_id=cfg["chat_id"],
                content=text,
                chat_type=cfg["chat_type"],
            )
        if read_wecom_long_connection_enabled(config_path):
            raise RuntimeError(
                "智能机器人长连接尚未就绪，请查看 youzi_v2/logs/wecom-aibot-*.log 或稍后重试"
            )
        return send_text_via_session(
            ws_url=cfg["ws_url"],
            bot_id=cfg["bot_id"],
            secret=cfg["secret"],
            chat_id=cfg["chat_id"],
            content=text,
            chat_type=cfg["chat_type"],
        )
    payload = {"msgtype": "text", "text": {"content": text}}
    return _post_webhook(cfg["send_url"], payload, timeout=cfg["timeout"])


def send_wecom_markdown(config_path: Path, content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise ValueError("消息内容不能为空")
    cfg = require_wecom_webhook_config(config_path)
    if cfg["mode"] == "aibot":
        raise ValueError("智能机器人长连接模式暂仅支持 text；请改用 send_wecom_text 或配置 Webhook key")
    payload = {"msgtype": "markdown", "markdown": {"content": text}}
    return _post_webhook(cfg["send_url"], payload, timeout=cfg["timeout"])


def _post_webhook(send_url: str, payload: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    try:
        resp = requests.post(
            send_url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return {"ok": False, "errcode": -1, "errmsg": str(exc)}
    except ValueError as exc:
        return {"ok": False, "errcode": -1, "errmsg": f"响应非 JSON: {exc}"}

    errcode = int(data.get("errcode", -1))
    errmsg = str(data.get("errmsg") or "")
    return {
        "ok": errcode == 0,
        "errcode": errcode,
        "errmsg": errmsg,
    }


def webhook_key_configured(config_path: Path) -> bool:
    """是否已配置任一发送方式（不校验 enabled）。"""
    cfg = load_wecom_webhook_config(config_path)
    return cfg["mode"] != "none"


def redact_webhook_url(send_url: str) -> str:
    """日志/接口展示用，隐藏 key 参数。"""
    parsed = urlparse(send_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if "key" in qs:
        qs["key"] = ["***"]
    query = urlencode(qs, doseq=True)
    return parsed._replace(query=query).geturl()
