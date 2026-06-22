"""运单分组规则评估：签收期限、最后一批到港催款。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..db.connection import Database
from ..db.shipment_group_alerts_repository import ShipmentGroupAlertsRepository
from ..db.shipment_groups_table import GROUPS_TABLE, MEMBERS_TABLE
from ..db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from ..shipment_group_types import rule_applies_to_group_types


def _is_delivered(row: dict[str, Any]) -> bool:
    status = (row.get("status_code") or "").strip().upper()
    delivered = (row.get("delivered_time") or "").strip()
    return status == "DELIVERED" or bool(delivered)


def _delivered_dt(repo: ShipmentGroupAlertsRepository, row: dict[str, Any]) -> datetime | None:
    dt = repo.parse_dt(row.get("delivered_time"))
    if dt:
        return dt
    if (row.get("status_code") or "").strip().upper() == "DELIVERED":
        return repo.parse_dt(row.get("latest_tracking_time"))
    return None


def _has_arrived(repo: ShipmentGroupAlertsRepository, row: dict[str, Any]) -> bool:
    return repo.parse_dt(row.get("ata")) is not None


def _load_group_row(conn, group_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"SELECT * FROM {GROUPS_TABLE} WHERE id = ?",
        (group_id.strip(),),
    ).fetchone()
    if not row:
        return None
    return dict(row)


def _load_members_with_shipments(conn, group_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT m.id AS member_id, m.group_id, m.shipment_id, m.shipment_no,
               m.role, m.batch_no,
               s.status_code, s.delivered_time, s.latest_tracking_time, s.ata
        FROM {MEMBERS_TABLE} m
        INNER JOIN {SHIPMENTS_TABLE} s ON s.id = m.shipment_id
        WHERE m.group_id = ?
        ORDER BY m.shipment_no
        """,
        (group_id.strip(),),
    ).fetchall()
    return [dict(r) for r in rows]


def _evaluate_batch_delivery_deadline(
    repo: ShipmentGroupAlertsRepository,
    group: dict[str, Any],
    members: list[dict[str, Any]],
    rule: dict[str, Any],
) -> int:
    if not rule.get("enabled"):
        return 0
    threshold = int(rule.get("thresholdDays") or 30)
    warning_days = int(rule.get("warningDays") or 7)
    warning_offset = max(0, threshold - warning_days)

    batches: dict[str, list[dict[str, Any]]] = {}
    for m in members:
        batch_key = (m.get("batch_no") or "").strip() or "__default__"
        batches.setdefault(batch_key, []).append(m)

    created = 0
    group_id = group["id"]
    group_no = group["group_no"]
    now = datetime.now()

    for batch_key, batch_members in batches.items():
        delivered_times = [
            dt
            for m in batch_members
            if _is_delivered(m) and (dt := _delivered_dt(repo, m)) is not None
        ]
        if not delivered_times:
            continue
        first = min(delivered_times)
        undelivered = [m for m in batch_members if not _is_delivered(m)]
        if not undelivered:
            continue

        batch_label = batch_key if batch_key != "__default__" else "默认批次"
        first_date = first.strftime("%Y-%m-%d")
        days_since = (now - first).days
        undelivered_count = len(undelivered)

        if days_since >= threshold:
            event_key = f"{group_id}|DELIVERED_DEADLINE_OVERDUE|{batch_key}|{first_date}"
            if repo.upsert_notification(
                group_id=group_id,
                rule_type="BATCH_DELIVERY_DEADLINE",
                event_key=event_key,
                title="签收已超期，存在罚款风险",
                message=(
                    f"分组 {group_no} 批次 {batch_label} 第一票货物已于 {first_date} 签收，"
                    f"仍有 {undelivered_count} 票超过 {threshold} 天未签收，请尽快处理。"
                ),
                severity="urgent",
            ):
                created += 1
        elif days_since >= warning_offset:
            days_left = max(0, threshold - days_since)
            event_key = f"{group_id}|DELIVERED_DEADLINE_WARNING|{batch_key}|{first_date}"
            if repo.upsert_notification(
                group_id=group_id,
                rule_type="BATCH_DELIVERY_DEADLINE",
                event_key=event_key,
                title="签收期限将到期",
                message=(
                    f"分组 {group_no} 批次 {batch_label} 第一票货物已于 {first_date} 签收，"
                    f"仍有 {undelivered_count} 票未签收，距离 {threshold} 天罚款期限还有 "
                    f"{days_left} 天，请提前跟进。"
                ),
                severity="warning",
            ):
                created += 1
    return created


def _evaluate_last_batch_payment(
    repo: ShipmentGroupAlertsRepository,
    group: dict[str, Any],
    members: list[dict[str, Any]],
    rule: dict[str, Any],
) -> int:
    if not rule.get("enabled"):
        return 0
    payment_status = (group.get("payment_status") or "UNPAID").strip().upper()
    if payment_status == "PAID":
        return 0

    last_batch = [m for m in members if (m.get("role") or "").strip().upper() == "LAST_BATCH"]
    scope = last_batch if last_batch else members
    if not scope:
        return 0
    if not all(_has_arrived(repo, m) for m in scope):
        return 0

    arrival_dates = [repo.parse_dt(m.get("ata")) for m in scope]
    arrival_dates = [d for d in arrival_dates if d is not None]
    if not arrival_dates:
        return 0
    arrival = max(arrival_dates)
    arrival_date = arrival.strftime("%Y-%m-%d")

    group_id = group["id"]
    group_no = group["group_no"]
    event_key = f"{group_id}|LAST_BATCH_ARRIVED_PAYMENT|{arrival_date}"
    if repo.upsert_notification(
        group_id=group_id,
        rule_type="LAST_BATCH_ARRIVED_PAYMENT",
        event_key=event_key,
        title="最后一批已到港，请催款",
        message=(
            f"分组 {group_no} 最后一批货已到港，当前收款状态为 {payment_status}，请及时催款。"
        ),
        severity="warning",
    ):
        return 1
    return 0


def evaluate_group_alerts(
    database: Database,
    alerts_repo: ShipmentGroupAlertsRepository,
    *,
    group_id: str | None = None,
) -> dict[str, Any]:
    """评估一个或全部分组的提醒规则。"""
    group_ids = alerts_repo.list_group_ids(group_id=group_id)
    evaluated = 0
    created = 0
    errors: list[dict[str, str]] = []

    for gid in group_ids:
        try:
            alerts_repo.ensure_default_rules(gid)
            with database.lock:
                group = _load_group_row(database.conn, gid)
                if not group:
                    continue
                members = _load_members_with_shipments(database.conn, gid)
            if not members:
                evaluated += 1
                continue

            active_types = frozenset(alerts_repo.list_group_types(gid))
            delivery_rule = alerts_repo.get_rule(gid, "BATCH_DELIVERY_DEADLINE")
            payment_rule = alerts_repo.get_rule(gid, "LAST_BATCH_ARRIVED_PAYMENT")
            if (
                delivery_rule
                and delivery_rule.get("enabled")
                and rule_applies_to_group_types("BATCH_DELIVERY_DEADLINE", active_types)
            ):
                created += _evaluate_batch_delivery_deadline(
                    alerts_repo, group, members, delivery_rule
                )
            if (
                payment_rule
                and payment_rule.get("enabled")
                and rule_applies_to_group_types("LAST_BATCH_ARRIVED_PAYMENT", active_types)
            ):
                created += _evaluate_last_batch_payment(
                    alerts_repo, group, members, payment_rule
                )
            evaluated += 1
        except Exception as exc:  # noqa: BLE001 — 单组失败不阻断全量扫描
            errors.append({"groupId": gid, "message": str(exc)})

    return {
        "evaluated": evaluated,
        "created": created,
        "errors": errors,
    }


def evaluate_groups_for_shipment_ids(
    database: Database,
    alerts_repo: ShipmentGroupAlertsRepository,
    shipment_ids: list[str],
) -> dict[str, Any]:
    group_ids = alerts_repo.list_group_ids_for_shipments(shipment_ids)
    if not group_ids:
        return {"evaluated": 0, "created": 0, "errors": []}
    total_evaluated = 0
    total_created = 0
    errors: list[dict[str, str]] = []
    for gid in group_ids:
        result = evaluate_group_alerts(database, alerts_repo, group_id=gid)
        total_evaluated += int(result.get("evaluated") or 0)
        total_created += int(result.get("created") or 0)
        errors.extend(result.get("errors") or [])
    return {
        "evaluated": total_evaluated,
        "created": total_created,
        "errors": errors,
    }
