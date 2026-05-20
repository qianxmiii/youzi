"""轨迹同步过程日志：内存列表 + 控制台 + 本地 logs/ 文件（已 gitignore）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

LogFn = Callable[[str], None]

_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def _append_local_log(msg: str) -> None:
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        day = datetime.now().strftime("%Y-%m-%d")
        path = _LOG_DIR / f"tracking-sync-{day}.log"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass


def make_sync_logger(extra: LogFn | None = None) -> tuple[list[str], LogFn]:
    lines: list[str] = []

    def out_log(msg: str) -> None:
        lines.append(msg)
        print(msg, flush=True)
        _append_local_log(msg)
        if extra is not None:
            extra(msg)

    return lines, out_log
