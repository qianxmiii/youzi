"""运单订阅更新 → 企业微信主动推送（与顶栏铃铛同源通知）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .wecom_aibot_log import append_wecom_aibot_log
from .wecom_webhook import CONFIG_KEY, load_wecom_webhook_config, send_wecom_text

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "config.json"

_SOURCE_LABEL: dict[str, str] = {
    "internal": "内部轨迹",
    "carrier": "承运商轨迹",
    "eta_reminder": "到港提醒",
    "arrival": "到港",
}


def read_subscription_push_enabled(config_path: Path | None = None) -> bool:
    path = config_path or _DEFAULT_CONFIG_PATH
    if not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    block = data.get(CONFIG_KEY) if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return False
    explicit = block.get("subscription_push_enabled")
    if explicit is None:
        explicit = block.get("subscriptionPushEnabled")
    if explicit is not None:
        return bool(explicit)
    cfg = load_wecom_webhook_config(path)
    return bool(cfg.get("enabled"))


def format_subscription_push_message(payload: dict[str, Any]) -> str:
    sn = (payload.get("shipmentNo") or "").strip() or "—"
    source = (payload.get("trackingSource") or "").strip()
    label = _SOURCE_LABEL.get(source, source or "更新")
    latest_time = (payload.get("latestTime") or "").strip()
    latest_desc = (payload.get("latestDesc") or "").strip()
    lines = [f"【订阅更新】{sn}", label]
    if latest_time:
        lines.append(latest_time)
    if latest_desc:
        lines.append(latest_desc)
    return "\n".join(lines)


def try_push_subscription_notification(
    payload: dict[str, Any],
    *,
    config_path: Path | None = None,
) -> None:
    """推送失败只记日志，不影响写库与顶栏通知。"""
    path = config_path or _DEFAULT_CONFIG_PATH
    if not read_subscription_push_enabled(path):
        return
    cfg = load_wecom_webhook_config(path)
    if not cfg.get("enabled"):
        return
    if cfg.get("mode") == "aibot" and not (cfg.get("chat_id") or "").strip():
        append_wecom_aibot_log(
            "订阅更新未推送企微：智能机器人模式缺少 chat_id（见 docs/wecom-aibot.md）"
        )
        return
    text = format_subscription_push_message(payload)
    try:
        result = send_wecom_text(path, text)
    except Exception as exc:  # noqa: BLE001
        append_wecom_aibot_log(f"订阅更新推送企微失败: {exc}")
        return
    if not result.get("ok"):
        append_wecom_aibot_log(
            f"订阅更新推送企微失败 errcode={result.get('errcode')} "
            f"errmsg={result.get('errmsg')}"
        )
