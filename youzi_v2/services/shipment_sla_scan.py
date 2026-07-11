"""扫描未签收运单，按运输时效规则与阶段卡点生成/更新预警。"""

from __future__ import annotations

import threading
from datetime import date
from typing import Any, Callable

from ..db.channel_sla_rules_repository import ChannelSlaRulesRepository
from ..db.shipment_sla import (
    ACTIVE_STATUSES,
    ALERT_ARRIVAL_NO_DELIVERY,
    ALERT_DELIVERY_TIME,
    ALERT_WAREHOUSE_NO_DEPARTURE,
    build_event_key,
    compute_arrival_no_delivery_context,
    compute_due_context,
    compute_risk_level,
    compute_warehouse_no_departure_context,
    has_departure_schedule,
    is_delivered,
    is_sla_excluded_channel,
    match_channel_rule,
    parse_date,
)
from ..db.shipment_sla_alerts_repository import ShipmentSlaAlertsRepository
from ..db.shipment_exception_followup_repository import ShipmentExceptionFollowupRepository
from .shipment_sla_schedule import should_run_sla_scan
from .shipment_sla_settings import record_sla_scan_finished

LogFn = Callable[[str], None]

_lock = threading.Lock()

RISK_LABEL = {
    "warning_soon": "即将超时",
    "overdue": "已超时",
    "severe_overdue": "严重超时",
}

ALERT_TYPE_LABEL = {
    ALERT_DELIVERY_TIME: "运输时效",
    ALERT_WAREHOUSE_NO_DEPARTURE: "入库未开船",
    ALERT_ARRIVAL_NO_DELIVERY: "到港未送仓",
}


def _alert_log_label(alert_type: str, risk_level: str) -> str:
    type_label = ALERT_TYPE_LABEL.get(alert_type, alert_type)
    risk_label = RISK_LABEL.get(risk_level, risk_level)
    if alert_type == ALERT_DELIVERY_TIME:
        return risk_label
    return type_label


def _try_upsert_alert(
    alerts_repo: ShipmentSlaAlertsRepository,
    *,
    row: dict[str, Any],
    shipment_id: str,
    shipment_no: str,
    ctx: dict[str, Any],
    channel_code: str,
    carrier_code: str,
) -> tuple[bool, bool]:
    """返回 (is_new, should_skip_terminal)."""
    alert_type = str(ctx.get("alertType") or ALERT_DELIVERY_TIME)
    event_key = build_event_key(
        shipment_id=shipment_id,
        alert_type=alert_type,
        rule_id=str(ctx.get("ruleId") or ""),
        due_date=str(ctx["dueDate"]),
        anchor_date=str(ctx.get("startTime") or ctx["dueDate"]),
    )
    existing = alerts_repo.get_by_event_key(event_key)
    if existing and existing["status"] not in ACTIVE_STATUSES:
        return False, True

    risk_level = str(ctx.get("riskLevel") or ctx.get("risk_level") or "")
    if not risk_level and alert_type == ALERT_DELIVERY_TIME:
        return False, False

    is_new = alerts_repo.upsert_alert(
        shipment_id=shipment_id,
        shipment_no=shipment_no,
        risk_level=risk_level,
        event_key=event_key,
        due_date=str(ctx["dueDate"]),
        warning_date=str(ctx.get("warningDate") or ctx["dueDate"]),
        rule_id=str(ctx.get("ruleId") or ""),
        rule_scope=str(ctx.get("ruleScope") or ""),
        channel_code=channel_code,
        carrier_code=carrier_code,
        start_field=str(ctx.get("startField") or ""),
        start_time=str(ctx.get("startTime") or ""),
        alert_type=alert_type,
    )
    return is_new, False


def _scan_warehouse_no_departure(
    alerts_repo: ShipmentSlaAlertsRepository,
    *,
    row: dict[str, Any],
    shipment_id: str,
    shipment_no: str,
    channel_code: str,
    carrier_code: str,
    today: date,
) -> tuple[int, int, int]:
    created = updated = resolved = 0
    if has_departure_schedule(row):
        resolved += alerts_repo.resolve_open_for_shipment(
            shipment_id, alert_type=ALERT_WAREHOUSE_NO_DEPARTURE
        )
        return created, updated, resolved

    ctx = compute_warehouse_no_departure_context(row, today=today)
    if not ctx:
        resolved += alerts_repo.resolve_open_for_shipment(
            shipment_id, alert_type=ALERT_WAREHOUSE_NO_DEPARTURE
        )
        return created, updated, resolved

    is_new, _ = _try_upsert_alert(
        alerts_repo,
        row=row,
        shipment_id=shipment_id,
        shipment_no=shipment_no,
        ctx=ctx,
        channel_code=channel_code,
        carrier_code=carrier_code,
    )
    if is_new:
        created += 1
    else:
        updated += 1
    return created, updated, resolved


def _scan_arrival_no_delivery(
    alerts_repo: ShipmentSlaAlertsRepository,
    *,
    row: dict[str, Any],
    shipment_id: str,
    shipment_no: str,
    channel_code: str,
    carrier_code: str,
    today: date,
) -> tuple[int, int, int]:
    created = updated = resolved = 0
    ctx = compute_arrival_no_delivery_context(row, today=today)
    if not ctx:
        resolved += alerts_repo.resolve_open_for_shipment(
            shipment_id, alert_type=ALERT_ARRIVAL_NO_DELIVERY
        )
        return created, updated, resolved

    is_new, _ = _try_upsert_alert(
        alerts_repo,
        row=row,
        shipment_id=shipment_id,
        shipment_no=shipment_no,
        ctx=ctx,
        channel_code=channel_code,
        carrier_code=carrier_code,
    )
    if is_new:
        created += 1
    else:
        updated += 1
    return created, updated, resolved


def _scan_delivery_time(
    alerts_repo: ShipmentSlaAlertsRepository,
    rules_by_channel: dict[str, list[dict[str, Any]]],
    *,
    row: dict[str, Any],
    shipment_id: str,
    shipment_no: str,
    channel_code: str,
    carrier_code: str,
    today: date,
) -> tuple[int, int, int]:
    created = updated = resolved = 0
    rule = match_channel_rule(
        rules_by_channel,
        channel_code=channel_code,
        carrier_code=carrier_code,
    )
    ctx = compute_due_context(row, rule)
    if not ctx:
        resolved += alerts_repo.resolve_open_for_shipment(
            shipment_id, alert_type=ALERT_DELIVERY_TIME
        )
        return created, updated, resolved

    due_day = parse_date(ctx["dueDate"])
    if not due_day:
        return created, updated, resolved

    risk_level = compute_risk_level(
        today=today,
        due_day=due_day,
        warning_days=int(ctx["warningDays"]),
        severe_overdue_days=int(ctx["severeOverdueDays"]),
    )
    if not risk_level:
        resolved += alerts_repo.resolve_open_for_shipment(
            shipment_id, alert_type=ALERT_DELIVERY_TIME
        )
        return created, updated, resolved

    ctx = {**ctx, "riskLevel": risk_level}
    is_new, skip = _try_upsert_alert(
        alerts_repo,
        row=row,
        shipment_id=shipment_id,
        shipment_no=shipment_no,
        ctx=ctx,
        channel_code=channel_code,
        carrier_code=carrier_code,
    )
    if skip:
        return created, updated, resolved
    if is_new:
        created += 1
    else:
        updated += 1
    return created, updated, resolved


def scan_shipment_sla_alerts(
    alerts_repo: ShipmentSlaAlertsRepository,
    rules_repo: ChannelSlaRulesRepository,
    followup_repo: ShipmentExceptionFollowupRepository | None = None,
    *,
    force: bool = False,
    trigger: str = "scheduled",
    shipment_ids: list[str] | None = None,
    log: LogFn | None = None,
) -> dict[str, Any]:
    database = alerts_repo._database

    def out(msg: str) -> None:
        if log:
            log(msg)

    if not force and trigger == "scheduled":
        ok, reason = should_run_sla_scan(database)
        if not ok:
            out(f"[运输时效] 跳过：{reason}")
            return {"skipped": True, "reason": reason, "scanned": 0, "created": 0, "updated": 0}

    if not _lock.acquire(blocking=False):
        out("[运输时效] 跳过：上一轮仍在进行")
        return {
            "skipped": True,
            "reason": "运输时效扫描进行中",
            "scanned": 0,
            "created": 0,
            "updated": 0,
        }

    try:
        today = date.today()
        rules_by_channel = rules_repo.list_enabled_grouped()

        stale_resolved = alerts_repo.resolve_delivered_stale_alerts()
        if stale_resolved and followup_repo:
            followup_repo.resolve_pending_for_delivered_shipments()
        if stale_resolved:
            out(f"[运输时效] 兜底清理已签收预警 {stale_resolved} 条")

        excluded_resolved = alerts_repo.resolve_excluded_channel_alerts()
        if excluded_resolved:
            out(f"[运输时效] 关闭排除渠道预警 {excluded_resolved} 条")

        rows = alerts_repo.list_undelivered_shipments()
        if shipment_ids:
            wanted = {i.strip() for i in shipment_ids if i and i.strip()}
            rows = [r for r in rows if str(r.get("id") or "").strip() in wanted]

        created = 0
        updated = 0
        resolved = excluded_resolved
        scanned = len(rows)

        for row in rows:
            shipment_id = str(row.get("id") or "").strip()
            shipment_no = (row.get("shipment_no") or "").strip()
            if not shipment_id or not shipment_no:
                continue

            if is_delivered(row):
                n = alerts_repo.resolve_open_for_shipment(shipment_id)
                if n and followup_repo:
                    followup_repo.resolve_all_pending_for_shipment(shipment_no)
                resolved += n
                continue

            channel_code = (row.get("channel_code") or "").strip()
            carrier_code = (row.get("carrier_code") or "").strip()

            if is_sla_excluded_channel(channel_code):
                n = alerts_repo.resolve_open_for_shipment(shipment_id)
                if n and followup_repo:
                    followup_repo.resolve_all_pending_for_shipment(shipment_no)
                resolved += n
                continue

            wh_c, wh_u, wh_r = _scan_warehouse_no_departure(
                alerts_repo,
                row=row,
                shipment_id=shipment_id,
                shipment_no=shipment_no,
                channel_code=channel_code,
                carrier_code=carrier_code,
                today=today,
            )
            ar_c, ar_u, ar_r = _scan_arrival_no_delivery(
                alerts_repo,
                row=row,
                shipment_id=shipment_id,
                shipment_no=shipment_no,
                channel_code=channel_code,
                carrier_code=carrier_code,
                today=today,
            )
            dt_c, dt_u, dt_r = _scan_delivery_time(
                alerts_repo,
                rules_by_channel,
                row=row,
                shipment_id=shipment_id,
                shipment_no=shipment_no,
                channel_code=channel_code,
                carrier_code=carrier_code,
                today=today,
            )
            created += wh_c + ar_c + dt_c
            updated += wh_u + ar_u + dt_u
            resolved += wh_r + ar_r + dt_r

        if trigger == "scheduled" or force:
            record_sla_scan_finished(database)

        out(f"[运输时效] 扫描 {scanned} 单，新建 {created}，更新 {updated}，关闭 {resolved}")
        return {
            "skipped": False,
            "scanned": scanned,
            "created": created,
            "updated": updated,
            "resolved": resolved,
        }
    finally:
        _lock.release()


def evaluate_sla_after_tracking_sync(
    database,
    shipment_nos: list[str],
    log: LogFn | None = None,
) -> dict[str, Any]:
    from ..db.channel_sla_rules_repository import ChannelSlaRulesRepository
    from ..db.shipment_exception_followup_repository import ShipmentExceptionFollowupRepository
    from ..db.shipment_sla_alerts_repository import ShipmentSlaAlertsRepository
    from ..db.shipments_repository import ShipmentsRepository

    alerts_repo = ShipmentSlaAlertsRepository(database)
    rules_repo = ChannelSlaRulesRepository(database)
    followup_repo = ShipmentExceptionFollowupRepository(database)

    nos = list(dict.fromkeys(n.strip() for n in shipment_nos if n and n.strip()))
    if not nos:
        return {
            "slaAlertsScanned": 0,
            "slaAlertsCreated": 0,
            "slaAlertsUpdated": 0,
            "slaAlertsResolved": 0,
        }
    ids = ShipmentsRepository(database).list_ids_by_shipment_nos(nos)
    if not ids:
        return {
            "slaAlertsScanned": 0,
            "slaAlertsCreated": 0,
            "slaAlertsUpdated": 0,
            "slaAlertsResolved": 0,
        }
    result = scan_shipment_sla_alerts(
        alerts_repo,
        rules_repo,
        followup_repo,
        force=True,
        trigger="tracking_sync",
        shipment_ids=ids,
        log=log,
    )
    if log and not result.get("skipped"):
        created = int(result.get("created") or 0)
        if created:
            log(f"[运输时效] 轨迹同步后评估 {result.get('scanned')} 单，新建 {created} 条预警")
    return {
        "slaAlertsScanned": int(result.get("scanned") or 0),
        "slaAlertsCreated": int(result.get("created") or 0),
        "slaAlertsUpdated": int(result.get("updated") or 0),
        "slaAlertsResolved": int(result.get("resolved") or 0),
    }


def resolve_sla_alerts_after_delivery(
    alerts_repo: ShipmentSlaAlertsRepository,
    followup_repo: ShipmentExceptionFollowupRepository,
    *,
    shipment_ids: list[str],
    shipment_nos: list[str],
) -> int:
    resolved = alerts_repo.resolve_open_for_shipment_ids(shipment_ids)
    for sn in shipment_nos:
        if sn and sn.strip():
            followup_repo.resolve_all_pending_for_shipment(sn.strip())
    return resolved


def maybe_resolve_alerts_after_delivery(
    database,
    shipment_id: str,
    *,
    shipment_no: str | None = None,
    log: LogFn | None = None,
) -> int:
    """运单写入签收时间或状态变为已签收后，立即关闭时效预警与跟进待办。"""
    from ..db.shipment_exception_followup_repository import (
        ShipmentExceptionFollowupRepository,
    )
    from ..db.shipment_sla import is_delivered
    from ..db.shipment_sla_alerts_repository import ShipmentSlaAlertsRepository
    from ..db.shipments_repository import ShipmentsRepository

    sid = (shipment_id or "").strip()
    if not sid:
        return 0
    shipments_repo = ShipmentsRepository(database)
    row = shipments_repo.get_by_id(sid)
    if row is None:
        return 0
    if not is_delivered(
        {
            "status_code": row.get("statusCode"),
            "delivered_time": row.get("deliveredTime"),
        }
    ):
        return 0
    alerts_repo = ShipmentSlaAlertsRepository(database)
    followup_repo = ShipmentExceptionFollowupRepository(database)
    n = alerts_repo.resolve_open_for_shipment(sid)
    sn = (shipment_no or row.get("shipmentNo") or "").strip()
    if sn:
        followup_repo.resolve_all_pending_for_shipment(sn)
    if log and n:
        log(f"[运输时效] {sn} 已签收，关闭 {n} 条预警")
    return n
