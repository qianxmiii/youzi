"""定时全量轨迹同步：内部路由 + 承运商（仅转运中 IN_TRANSIT）。"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Callable

from ..db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from ..db.shipments_repository import ShipmentsRepository
from ..db.tracking_logs_repository import TrackingLogsRepository
from ..db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from .carrier_batch_schedule import (
    carrier_batch_interval_hours,
    get_last_carrier_batch_finished,
)
from .carrier_tracking_sync import sync_carrier_tracking
from .sync_log import make_sync_logger
from .tracking_sync import sync_all_tracking

LogFn = Callable[[str], None]

_lock = threading.Lock()


def run_scheduled_tracking_sync(
    shipments_repo: ShipmentsRepository,
    internal_repo: TrackingLogsRepository,
    carrier_repo: CarrierTrackingLogsRepository,
    jobs_repo: TrackingSyncJobsRepository,
    config_path: Path,
    *,
    log: LogFn | None = None,
) -> dict[str, Any]:
    """串行执行全库内部轨迹与承运商轨迹同步；若已有任务在跑则跳过。"""
    if not _lock.acquire(blocking=False):
        _, out_log = make_sync_logger(log)
        out_log("[定时同步] 跳过：上一轮同步仍在进行")
        return {"skipped": True, "reason": "already_running"}

    try:
        _, out_log = make_sync_logger(log)
        last_carrier = get_last_carrier_batch_finished(shipments_repo._database)
        interval_h = carrier_batch_interval_hours()
        out_log(
            "[定时同步] 开始：内部轨迹 → 承运商轨迹"
            + (
                f"（承运商全库间隔 {interval_h:g}h，上次 {last_carrier or '无'}）"
                if interval_h > 0
                else ""
            )
        )
        internal = sync_all_tracking(
            shipments_repo,
            internal_repo,
            config_path,
            shipment_nos=None,
            log=out_log,
        )
        carrier = sync_carrier_tracking(
            shipments_repo,
            carrier_repo,
            jobs_repo,
            config_path,
            trigger="scheduled",
            shipment_nos=None,
            log=out_log,
        )
        carrier_note = ""
        if carrier.get("intervalSkipped"):
            carrier_note = f"，承运商已跳过（{carrier.get('skipReason', '')}）"
        out_log(
            "[定时同步] 完成："
            f"内部更新 {internal.get('updated', 0)} 单，"
            f"承运更新 {carrier.get('updated', 0)} 单"
            + carrier_note
        )
        return {"skipped": False, "internal": internal, "carrier": carrier}
    except Exception as exc:
        _, out_log = make_sync_logger(log)
        out_log(f"[定时同步] 失败: {exc}")
        raise
    finally:
        _lock.release()


def start_tracking_sync_scheduler(
    shipments_repo: ShipmentsRepository,
    internal_repo: TrackingLogsRepository,
    carrier_repo: CarrierTrackingLogsRepository,
    jobs_repo: TrackingSyncJobsRepository,
    config_path: Path,
) -> threading.Event:
    """
    后台线程：首次延迟后执行，此后每 N 小时一轮。
    环境变量：
      YOUZI_TRACKING_SYNC_INTERVAL_HOURS — 间隔小时数，默认 2；设为 0 关闭
      YOUZI_TRACKING_SYNC_INITIAL_DELAY_SEC — 首次延迟秒数，默认 60
    """
    interval_hours = float(os.getenv("YOUZI_TRACKING_SYNC_INTERVAL_HOURS", "2"))
    initial_delay = float(os.getenv("YOUZI_TRACKING_SYNC_INITIAL_DELAY_SEC", "60"))
    stop = threading.Event()

    if interval_hours <= 0:
        print("[定时同步] 已关闭（YOUZI_TRACKING_SYNC_INTERVAL_HOURS<=0）", flush=True)
        return stop

    interval_sec = max(60.0, interval_hours * 3600.0)
    initial_sec = max(0.0, initial_delay)

    def worker() -> None:
        if stop.wait(initial_sec):
            return
        while not stop.is_set():
            try:
                run_scheduled_tracking_sync(
                    shipments_repo,
                    internal_repo,
                    carrier_repo,
                    jobs_repo,
                    config_path,
                )
            except Exception:
                pass
            if stop.wait(interval_sec):
                break

    thread = threading.Thread(
        target=worker,
        name="youzi-tracking-sync",
        daemon=True,
    )
    thread.start()
    print(
        f"[定时同步] 已启动：{initial_sec:.0f}s 后首次执行，之后每 {interval_hours:g} 小时；"
        f"承运商全库未满 {interval_hours:g} 小时则跳过（重启不重复拉取）",
        flush=True,
    )
    return stop
