"""扫描标记异常运单，按分档间隔生成跟进待办。"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Callable

from ..db.exception_followup import (
    followup_interval_days,
    followup_severity,
    is_followup_due,
)
from ..db.shipment_exception_followup_repository import ShipmentExceptionFollowupRepository
from .exception_followup_settings import record_exception_followup_scan_finished
from .exception_followup_schedule import should_run_exception_followup_scan

LogFn = Callable[[str], None]

_lock = threading.Lock()


def _build_message(
    *,
    shipment_no: str,
    exception_label: str,
    days_open: int,
    interval: int,
) -> str:
    if days_open >= 20:
        tier_hint = f"异常已持续 {days_open} 天，当前每 {interval} 天需跟进一次。"
    elif days_open >= 10:
        tier_hint = (
            f"异常已持续 {days_open} 天（≥10 天每 5 天 / ≥20 天每 7 天），请跟进。"
        )
    else:
        tier_hint = f"异常已持续 {days_open} 天（10 天以内每 3 天跟进），请确认处理进展。"
    return f"运单 {shipment_no} · {exception_label}。{tier_hint}"


def scan_exception_followup_reminders(
    repo: ShipmentExceptionFollowupRepository,
    *,
    force: bool = False,
    trigger: str = "scheduled",
    log: LogFn | None = None,
) -> dict[str, Any]:
    database = repo._database

    def out(msg: str) -> None:
        if log:
            log(msg)

    if not force:
        ok, reason = should_run_exception_followup_scan(database)
        if not ok:
            out(f"[异常跟进] 跳过：{reason}")
            return {"skipped": True, "reason": reason, "scanned": 0, "created": 0}

    if not _lock.acquire(blocking=False):
        out("[异常跟进] 跳过：上一轮仍在进行")
        return {"skipped": True, "reason": "异常跟进扫描进行中", "scanned": 0, "created": 0}

    try:
        now = datetime.now()
        today_key = now.strftime("%Y%m%d")
        rows = repo.list_active_exception_shipments()
        created = 0
        scanned = len(rows)

        for row in rows:
            sn = (row.get("shipment_no") or "").strip()
            opened = (row.get("exception_opened_time") or "").strip()
            if not sn or not opened:
                continue
            if repo.has_pending_followup(sn):
                continue

            anchor = repo.last_followup_anchor(sn)
            due, days_open, interval = is_followup_due(opened, anchor, now=now)
            if not due:
                continue

            exc_code = (row.get("exception_code") or "").strip()
            exc_label = (row.get("exception_name_zh") or exc_code or "异常").strip()
            severity = followup_severity(days_open)
            title = "异常跟进提醒"
            message = _build_message(
                shipment_no=sn,
                exception_label=exc_label,
                days_open=days_open,
                interval=interval,
            )
            event_key = f"exception_followup:{sn}:{today_key}"
            if repo.create_followup_notification(
                shipment_id=str(row.get("id") or ""),
                shipment_no=sn,
                exception_code=exc_code,
                title=title,
                message=message,
                severity=severity,
                days_open=days_open,
                followup_interval_days=interval,
                event_key=event_key,
            ):
                created += 1
                out(f"[异常跟进] 新建待办 {sn}（{days_open} 天 / 每 {interval} 天）")

        if trigger == "scheduled" or force:
            record_exception_followup_scan_finished(database)

        out(f"[异常跟进] 扫描 {scanned} 单，新建 {created} 条待办")
        return {"skipped": False, "scanned": scanned, "created": created}
    finally:
        _lock.release()
