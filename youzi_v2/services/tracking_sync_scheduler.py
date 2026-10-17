"""定时轨迹同步：内部路由与承运商独立开关、独立间隔。"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from ..db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from ..db.connection import Database
from ..db.shipments_repository import ShipmentsRepository
from ..db.shipment_exception_followup_repository import ShipmentExceptionFollowupRepository
from ..db.channel_sla_rules_repository import ChannelSlaRulesRepository
from ..db.shipment_sla_alerts_repository import ShipmentSlaAlertsRepository
from ..db.shipment_groups_repository import ShipmentGroupsRepository
from ..db.tracking_logs_repository import TrackingLogsRepository
from ..db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from ..db.shipment_subscriptions_table import ShipmentSubscriptionsRepository
from .carrier_tracking_sync import sync_carrier_tracking
from .group_archive_settings import get_group_archive_settings
from .scheduled_sync_settings import get_scheduled_sync_settings
from .shipment_group_archive import run_group_auto_archive_batch
from .shipment_zipcode_backfill import run_zipcode_backfill_batch
from .shipment_dps_sync import run_shipment_dps_sync_batch
from .exception_followup_reminders import scan_exception_followup_reminders
from .shipment_sla_scan import scan_shipment_sla_alerts
from .shipment_sla_settings import get_sla_scan_settings
from .zipcode_backfill_settings import get_zipcode_backfill_settings
from .exception_followup_settings import get_exception_followup_settings
from .shipment_dps_sync_settings import get_shipment_dps_sync_settings
from .sync_log import make_sync_logger
from .tracking_sync import sync_all_tracking

LogFn = Callable[[str], None]

_internal_lock = threading.Lock()
_carrier_lock = threading.Lock()
_eta_reminder_lock = threading.Lock()

POLL_INTERVAL_SEC = 60.0


def run_subscription_eta_reminders(
    database: Database,
    *,
    log: LogFn | None = None,
) -> dict[str, Any]:
    """扫描已订阅运单的 ETA 到港提醒（按日去重）。"""

    def out(msg: str) -> None:
        if log:
            log(msg)

    if not _eta_reminder_lock.acquire(blocking=False):
        out("[订阅ETA提醒] 跳过：上一轮仍在进行")
        return {"skipped": True, "reason": "进行中"}
    try:
        result = ShipmentSubscriptionsRepository(database).evaluate_eta_reminders()
        created = int(result.get("created") or 0)
        if created:
            out(
                f"[订阅ETA提醒] scanned={result.get('scanned')} "
                f"created={created} skipped={result.get('skipped')}"
            )
        return {"skipped": False, **result}
    finally:
        _eta_reminder_lock.release()


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
    groups_repo: ShipmentGroupsRepository,
    exception_followup_repo: ShipmentExceptionFollowupRepository,
    channel_sla_rules_repo: ChannelSlaRulesRepository,
    shipment_sla_alerts_repo: ShipmentSlaAlertsRepository,
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
    run_group_auto_archive_batch(groups_repo, force=False, trigger="scheduled")
    run_zipcode_backfill_batch(shipments_repo, force=False, trigger="scheduled")
    run_shipment_dps_sync_batch(
        shipments_repo,
        config_path,
        force=False,
        trigger="scheduled",
        variant="default",
    )
    run_shipment_dps_sync_batch(
        shipments_repo,
        config_path,
        force=False,
        trigger="scheduled",
        variant="pickup",
    )
    run_shipment_dps_sync_batch(
        shipments_repo,
        config_path,
        force=False,
        trigger="scheduled",
        variant="warehoused",
    )
    scan_exception_followup_reminders(
        exception_followup_repo,
        force=False,
        trigger="scheduled",
    )
    scan_shipment_sla_alerts(
        shipment_sla_alerts_repo,
        channel_sla_rules_repo,
        exception_followup_repo,
        force=False,
        trigger="scheduled",
    )
    run_subscription_eta_reminders(shipments_repo._database)


def start_tracking_sync_scheduler(
    shipments_repo: ShipmentsRepository,
    internal_repo: TrackingLogsRepository,
    carrier_repo: CarrierTrackingLogsRepository,
    jobs_repo: TrackingSyncJobsRepository,
    groups_repo: ShipmentGroupsRepository,
    exception_followup_repo: ShipmentExceptionFollowupRepository,
    channel_sla_rules_repo: ChannelSlaRulesRepository,
    shipment_sla_alerts_repo: ShipmentSlaAlertsRepository,
    config_path: Path,
) -> threading.Event:
    """后台线程：按配置轮询，内部/承运商/分组归档各自判断间隔。"""
    database = shipments_repo._database
    settings = get_scheduled_sync_settings(database)
    group_archive_enabled = get_group_archive_settings(database).auto_archive_enabled
    zipcode_backfill_enabled = get_zipcode_backfill_settings(database).enabled
    dps_settings = get_shipment_dps_sync_settings(database)
    dps_sync_enabled = dps_settings.enabled
    dps_pickup_enabled = dps_settings.pickup_enabled
    dps_warehoused_enabled = dps_settings.warehoused_enabled
    exception_followup_enabled = get_exception_followup_settings(database).enabled
    sla_scan_enabled = get_sla_scan_settings(database).enabled
    stop = threading.Event()

    # 订阅 ETA 提醒始终启用；其它任务按各自开关
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
                    groups_repo,
                    exception_followup_repo,
                    channel_sla_rules_repo,
                    shipment_sla_alerts_repo,
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
        f"({settings.carrier_interval_hours:g}h)、"
        f"分组归档={'开' if group_archive_enabled else '关'}"
        f"(约24h)、"
        f"邮编回写={'开' if zipcode_backfill_enabled else '关'}"
        f"(约24h)、"
        f"DPS运单={'开' if dps_sync_enabled else '关'}"
        f"(约24h)、"
        f"DPS提货中={'开' if dps_pickup_enabled else '关'}"
        f"(约24h)、"
        f"DPS已入仓={'开' if dps_warehoused_enabled else '关'}"
        f"(约24h)、"
        f"异常跟进={'开' if exception_followup_enabled else '关'}"
        f"(约24h)、"
        f"运输时效={'开' if sla_scan_enabled else '关'}"
        f"(约24h)、"
        f"订阅ETA提醒=开；"
        f"{initial_sec:.0f}s 后首次检查，每 {POLL_INTERVAL_SEC:.0f}s 轮询",
        flush=True,
    )
    return stop
