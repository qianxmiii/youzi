"""定时轨迹同步：内部路由与承运商独立开关、独立间隔。"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from ..db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from ..db.connection import Database
from ..db.shipments_repository import ShipmentsRepository
from ..db.tracking_logs_repository import TrackingLogsRepository
from ..db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from .carrier_tracking_sync import sync_carrier_tracking
from .scheduled_sync_settings import get_scheduled_sync_settings
from .sync_log import make_sync_logger
from .tracking_sync import sync_all_tracking

LogFn = Callable[[str], None]

_internal_lock = threading.Lock()
_carrier_lock = threading.Lock()

POLL_INTERVAL_SEC = 60.0


def run_scheduled_internal_sync(
    shipments_repo: ShipmentsRepository,
    internal_repo: TrackingLogsRepository,
    jobs_repo: TrackingSyncJobsRepository,
    config_path: Path,
    *,
    force: bool = False,
    log: LogFn | None = None,
) -> dict[str, Any]:
    database = shipments_repo._database
    _, out_log = make_sync_logger(log)

    if not force and not get_scheduled_sync_settings(database).internal_enabled:
        out_log("[定时同步] 跳过内部轨迹：已关闭")
        return {"skipped": True, "reason": "内部轨迹定时同步已关闭"}

    if not _internal_lock.acquire(blocking=False):
        out_log("[定时同步] 跳过内部轨迹：上一轮仍在进行")
        return {"skipped": True, "reason": "内部轨迹同步进行中"}

    try:
        result = sync_all_tracking(
            shipments_repo,
            internal_repo,
            config_path,
            shipment_nos=None,
            jobs_repo=jobs_repo,
            trigger="scheduled" if not force else "manual",
            log=out_log,
        )
        if result.get("intervalSkipped"):
            return {"skipped": True, "reason": result.get("skipReason")}
        return {"skipped": False, "internal": result}
    finally:
        _internal_lock.release()


def run_scheduled_carrier_sync(
    shipments_repo: ShipmentsRepository,
    carrier_repo: CarrierTrackingLogsRepository,
    jobs_repo: TrackingSyncJobsRepository,
    config_path: Path,
    *,
    force: bool = False,
    log: LogFn | None = None,
) -> dict[str, Any]:
    database = shipments_repo._database
    _, out_log = make_sync_logger(log)

    if not force:
        settings = get_scheduled_sync_settings(database)
        if not settings.carrier_enabled:
            out_log("[定时同步] 跳过承运商轨迹：已关闭")
            return {"skipped": True, "reason": "承运商轨迹定时同步已关闭"}

    if not _carrier_lock.acquire(blocking=False):
        out_log("[定时同步] 跳过承运商轨迹：上一轮仍在进行")
        return {"skipped": True, "reason": "承运商轨迹同步进行中"}

    try:
        result = sync_carrier_tracking(
            shipments_repo,
            carrier_repo,
            jobs_repo,
            config_path,
            trigger="scheduled" if not force else "manual",
            shipment_nos=None,
            log=out_log,
        )
        if result.get("intervalSkipped"):
            return {"skipped": True, "reason": result.get("skipReason")}
        return {"skipped": False, "carrier": result}
    finally:
        _carrier_lock.release()


def run_scheduled_tracking_sync(
    shipments_repo: ShipmentsRepository,
    internal_repo: TrackingLogsRepository,
    carrier_repo: CarrierTrackingLogsRepository,
    jobs_repo: TrackingSyncJobsRepository,
    config_path: Path,
    *,
    force: bool = False,
    log: LogFn | None = None,
) -> dict[str, Any]:
    """依次尝试内部、承运商（各自受开关与间隔约束，除非 force）。"""
    internal = run_scheduled_internal_sync(
        shipments_repo,
        internal_repo,
        jobs_repo,
        config_path,
        force=force,
        log=log,
    )
    carrier = run_scheduled_carrier_sync(
        shipments_repo,
        carrier_repo,
        jobs_repo,
        config_path,
        force=force,
        log=log,
    )
    return {
        "skipped": bool(internal.get("skipped")) and bool(carrier.get("skipped")),
        "internal": internal,
        "carrier": carrier,
    }


def _scheduler_tick(
    shipments_repo: ShipmentsRepository,
    internal_repo: TrackingLogsRepository,
    carrier_repo: CarrierTrackingLogsRepository,
    jobs_repo: TrackingSyncJobsRepository,
    config_path: Path,
) -> None:
    settings = get_scheduled_sync_settings(shipments_repo._database)
    if settings.internal_enabled:
        run_scheduled_internal_sync(
            shipments_repo,
            internal_repo,
            jobs_repo,
            config_path,
            force=False,
        )
    if settings.carrier_enabled:
        run_scheduled_carrier_sync(
            shipments_repo,
            carrier_repo,
            jobs_repo,
            config_path,
            force=False,
        )


def start_tracking_sync_scheduler(
    shipments_repo: ShipmentsRepository,
    internal_repo: TrackingLogsRepository,
    carrier_repo: CarrierTrackingLogsRepository,
    jobs_repo: TrackingSyncJobsRepository,
    config_path: Path,
) -> threading.Event:
    """后台线程：按配置轮询，内部/承运商各自判断间隔。"""
    database = shipments_repo._database
    settings = get_scheduled_sync_settings(database)
    stop = threading.Event()

    if not settings.internal_enabled and not settings.carrier_enabled:
        print("[定时同步] 已关闭（内部与承运商均未启用）", flush=True)
        return stop

    initial_sec = max(0.0, settings.initial_delay_sec)

    def worker() -> None:
        if stop.wait(initial_sec):
            return
        while not stop.is_set():
            try:
                _scheduler_tick(
                    shipments_repo,
                    internal_repo,
                    carrier_repo,
                    jobs_repo,
                    config_path,
                )
            except Exception:
                pass
            if stop.wait(POLL_INTERVAL_SEC):
                break

    thread = threading.Thread(
        target=worker,
        name="youzi-tracking-sync",
        daemon=True,
    )
    thread.start()
    print(
        "[定时同步] 已启动："
        f"内部={'开' if settings.internal_enabled else '关'}"
        f"({settings.internal_interval_hours:g}h)、"
        f"承运商={'开' if settings.carrier_enabled else '关'}"
        f"({settings.carrier_interval_hours:g}h)；"
        f"{initial_sec:.0f}s 后首次检查，每 {POLL_INTERVAL_SEC:.0f}s 轮询",
        flush=True,
    )
    return stop
