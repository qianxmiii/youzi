"""同步日志格式化：时间戳前缀、API 报文 JSON。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

_DEFAULT_MAX_PAYLOAD = 12_000


def format_sync_log_line(msg: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{ts}] {msg}"


def format_api_payload_for_log(
    payload: Any,
    *,
    max_len: int = _DEFAULT_MAX_PAYLOAD,
) -> str:
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}…(截断，共 {len(text)} 字符)"
