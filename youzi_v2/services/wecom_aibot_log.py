"""企业微信智能机器人长连接运行日志（youzi_v2/logs/wecom-aibot-YYYY-MM-DD.log）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def append_wecom_aibot_log(message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line, flush=True)
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        day = datetime.now().strftime("%Y-%m-%d")
        path = _LOG_DIR / f"wecom-aibot-{day}.log"
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{line}\n")
    except OSError:
        pass
