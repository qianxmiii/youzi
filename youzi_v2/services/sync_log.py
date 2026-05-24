"""轨迹同步过程日志：内存列表 + 控制台 + 本地 logs/ 文件（已 gitignore）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from .sync_log_format import format_sync_log_line

LogFn = Callable[[str], None]

_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def _append_local_log(line: str) -> None:
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        day = datetime.now().strftime("%Y-%m-%d")
        path = _LOG_DIR / f"tracking-sync-{day}.log"
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{line}\n")
    except OSError:
        pass


def make_sync_logger(extra: LogFn | None = None) -> tuple[list[str], LogFn]:
    lines: list[str] = []

    def out_log(msg: str) -> None:
        line = format_sync_log_line(msg)
        lines.append(line)
        print(line, flush=True)
        _append_local_log(line)
        if extra is not None:
            extra(line)

    return lines, out_log
