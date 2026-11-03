"""拉取订单流转并写入本地快照。失败时不把已有订单标成已结束。"""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

from ..db.connection import Database
from ..db.datetime_util import now_str
from ..db.order_flow_repository import OrderFlowRepository
from .order_flow_client import fetch_order_flow_rows
from .order_flow_settings import (
    INTERVAL_SEC,
    get_order_flow_poll_settings,
    record_order_flow_poll_finished,
)

_lock = threading.Lock()


def _elapsed_sec(last_finished: str | None) -> float | None:
    text = (last_finished or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            started = datetime.strptime(text[:19], fmt)
            return (datetime.now() - started).total_seconds()
        except ValueError:
            continue
    return None


def run_order_flow_sync(
    database: Database,
    config_path: Path,
    *,
    force: bool = False,
) -> dict:
    settings = get_order_flow_poll_settings(database)
    if not force and not settings.enabled:
        return {"skipped": True, "reason": "disabled"}
    elapsed = _elapsed_sec(settings.last_finished)
    if not force and elapsed is not None and elapsed < INTERVAL_SEC:
        return {"skipped": True, "reason": "interval"}
    if not _lock.acquire(blocking=False):
        return {"skipped": True, "reason": "running"}
    try:
        remote = fetch_order_flow_rows(config_path)
        stats = OrderFlowRepository(database).apply_snapshot(remote)
        record_order_flow_poll_finished(database)
        print(
            f"[订单流转] {now_str()} 远端 {stats['remote']}，新增 {stats['created']}，"
            f"状态变化 {stats['changed']}，结束 {stats['ended']}",
            flush=True,
        )
        return {"skipped": False, "reason": "", **stats}
    finally:
        _lock.release()
