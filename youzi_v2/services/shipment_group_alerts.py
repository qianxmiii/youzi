"""运单分组规则评估：签收期限、整组到港催款。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from ..db.connection import Database
from ..db.shipment_group_alerts_repository import ShipmentGroupAlertsRepository
from ..db.shipment_groups_repository import format_group_no_display
from ..db.shipment_groups_table import GROUPS_TABLE, MEMBERS_TABLE
from ..db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from ..shipment_group_rules import (
    RULE_TYPE_BATCH_DELIVERY_DEADLINE,
    RULE_TYPE_GROUP_ARRIVED_PAYMENT,
    RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING,
    payment_status_label,
)


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
               s.status_code, s.delivered_time, s.latest_tracking_time, s.ata,
               s.eta, s.customer
        FROM {MEMBERS_TABLE} m
        INNER JOIN {SHIPMENTS_TABLE} s ON s.id = m.shipment_id
        WHERE m.group_id = ?
        ORDER BY m.shipment_no
        """,
        (group_id.strip(),),
    ).fetchall()
    return [dict(r) for r in rows]


def _resolve_group_customer(group: dict[str, Any], members: list[dict[str, Any]]) -> str:
    customer = (group.get("customer") or "").strip()
    if customer:
        return customer
    for m in members:
        c = (m.get("customer") or "").strip()
        if c:
            return c
    return ""


def _load_customer_in_transit_shipments(
    conn,
    customer: str,
) -> list[dict[str, Any]]:
    name = customer.strip()
    if not name:
        return []
    rows = conn.execute(
        f"""
        SELECT id, shipment_no, status_code, eta, ata, delivered_time, customer
        FROM {SHIPMENTS_TABLE}
        WHERE TRIM(customer) = ? COLLATE NOCASE
          AND status_code = 'IN_TRANSIT'
          AND (ata IS NULL OR TRIM(ata) = '')
          AND (delivered_time IS NULL OR TRIM(delivered_time) = '')
        ORDER BY shipment_no
        """,
        (name,),
    ).fetchall()
    return [dict(r) for r in rows]


def _evaluate_single_in_transit_eta_warning(
    repo: ShipmentGroupAlertsRepository,
    conn,
    group: dict[str, Any],
    members: list[dict[str, Any]],
    rule: dict[str, Any],
) -> int:
    if not rule.get("enabled"):
        return 0
    if not members:
        return 0

    customer = _resolve_group_customer(group, members)
    if not customer:
        return 0

    warning_days = int(rule.get("warningDays") or 10)
    in_transit = _load_customer_in_transit_shipments(conn, customer)
    if len(in_transit) != 1:
        return 0

    ship = in_transit[0]
    member_ids = {str(m.get("shipment_id") or "") for m in members}
    if str(ship.get("id") or "") not in member_ids:
        return 0

    eta_dt = repo.parse_dt(ship.get("eta"))
    if not eta_dt:
        return 0

    eta_day: date = eta_dt.date()
    today = datetime.now().date()
    days_until = (eta_day - today).days
    if days_until < 0 or days_until > warning_days:
        return 0

    group_id = group["id"]
    group_no = format_group_no_display(group["group_no"])
    shipment_no = (ship.get("shipment_no") or "").strip()
    eta_label = eta_day.strftime("%Y-%m-%d")
    event_key = f"{group_id}|SINGLE_IN_TRANSIT_ETA|{ship['id']}|{eta_label}"

    if days_until == 0:
        title = "单票在途货物今日预计到港"
        message = (
            f"客户 {customer} 当前仅有一票在途（{shipment_no}），"
            f"预计今日（{eta_label}）到港，请关注。"
        )
    else:
        title = "单票在途货物即将到港"
        message = (
            f"客户 {customer} 当前仅有一票在途（{shipment_no}），"
            f"预计 {eta_label} 到港，还有 {days_until} 天。"
        )

    if repo.upsert_notification(
        group_id=group_id,
        rule_type=RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING,
        event_key=event_key,
        title=title,
        message=message,
        severity="info",
        shipment_no=shipment_no,
    ):
        return 1
    return 0


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

    delivered_times = [
        dt
        for m in members
        if _is_delivered(m) and (dt := _delivered_dt(repo, m)) is not None
    ]
    if not delivered_times:
        return 0
    first = min(delivered_times)
    undelivered = [m for m in members if not _is_delivered(m)]
    if not undelivered:
        return 0

    group_id = group["id"]
    group_no = format_group_no_display(group["group_no"])
    now = datetime.now()
    first_date = first.strftime("%Y-%m-%d")
    days_since = (now - first).days
    undelivered_count = len(undelivered)

    created = 0
    if days_since >= threshold:
        event_key = f"{group_id}|DELIVERED_DEADLINE_OVERDUE|{first_date}"
        if repo.upsert_notification(
            group_id=group_id,
            rule_type=RULE_TYPE_BATCH_DELIVERY_DEADLINE,
            event_key=event_key,
            title="签收已超期，存在罚款风险",
            message=(
                f"分组 {group_no} 第一票货物已于 {first_date} 签收，"
                f"仍有 {undelivered_count} 票超过 {threshold} 天未签收，请尽快处理。"
            ),
            severity="urgent",
        ):
            created += 1
    elif days_since >= warning_offset:
        days_left = max(0, threshold - days_since)
        event_key = f"{group_id}|DELIVERED_DEADLINE_WARNING|{first_date}"
        if repo.upsert_notification(
            group_id=group_id,
            rule_type=RULE_TYPE_BATCH_DELIVERY_DEADLINE,
            event_key=event_key,
            title="签收期限将到期",
            message=(
                f"分组 {group_no} 第一票货物已于 {first_date} 签收，"
                f"仍有 {undelivered_count} 票未签收，距离 {threshold} 天罚款期限还有 "
                f"{days_left} 天，请提前跟进。"
            ),
            severity="warning",
        ):
            created += 1
    return created


def _evaluate_group_arrived_payment(
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
    if not members:
        return 0
    if not all(_has_arrived(repo, m) for m in members):
        return 0

    arrival_dates = [repo.parse_dt(m.get("ata")) for m in members]
    arrival_dates = [d for d in arrival_dates if d is not None]
    if not arrival_dates:
        return 0
    arrival = max(arrival_dates)
    arrival_date = arrival.strftime("%Y-%m-%d")

    group_id = group["id"]
    group_no = format_group_no_display(group["group_no"])
    event_key = f"{group_id}|GROUP_ARRIVED_PAYMENT|{arrival_date}"
    if repo.upsert_notification(
        group_id=group_id,
        rule_type=RULE_TYPE_GROUP_ARRIVED_PAYMENT,
        event_key=event_key,
        title="整组货物已到港，请催款",
        message=(
            f"{group_no} 组内货物已全部到港，当前收款状态为 "
            f"{payment_status_label(payment_status)}，请及时催款。"
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
    """评估一个或全部分组的提醒规则（仅依据 shipment_group_rules.enabled）。"""
    group_ids = alerts_repo.list_group_ids(group_id=group_id)
    evaluated = 0
    created = 0
    errors: list[dict[str, str]] = []

    for gid in group_ids:
        try:
            with database.lock:
                group = _load_group_row(database.conn, gid)
                if not group:
                    continue
                if (group.get("archived_at") or "").strip():
                    evaluated += 1
                    continue
                members = _load_members_with_shipments(database.conn, gid)
                conn = database.conn
            if not members:
                evaluated += 1
                continue

            delivery_rule = alerts_repo.get_rule(gid, RULE_TYPE_BATCH_DELIVERY_DEADLINE)
            payment_rule = alerts_repo.get_rule(gid, RULE_TYPE_GROUP_ARRIVED_PAYMENT)
            eta_rule = alerts_repo.get_rule(gid, RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING)
            if delivery_rule and delivery_rule.get("enabled"):
                try:
                    created += _evaluate_batch_delivery_deadline(
                        alerts_repo, group, members, delivery_rule
                    )
                except Exception as exc:  # noqa: BLE001 — 单条规则失败不阻断同组其它规则
                    errors.append({"groupId": gid, "message": f"签收期限: {exc}"})
            if payment_rule and payment_rule.get("enabled"):
                try:
                    created += _evaluate_group_arrived_payment(
                        alerts_repo, group, members, payment_rule
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append({"groupId": gid, "message": f"整组到港催款: {exc}"})
            if eta_rule and eta_rule.get("enabled"):
                try:
                    with database.lock:
                        created += _evaluate_single_in_transit_eta_warning(
                            alerts_repo, conn, group, members, eta_rule
                        )
                except Exception as exc:  # noqa: BLE001
                    errors.append({"groupId": gid, "message": f"单票在途到港: {exc}"})
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


def evaluate_groups_for_shipment_nos(
    database: Database,
    alerts_repo: ShipmentGroupAlertsRepository,
    shipment_nos: list[str],
) -> dict[str, Any]:
    from ..db.shipments_repository import ShipmentsRepository

    ids = ShipmentsRepository(database).list_ids_by_shipment_nos(shipment_nos)
    if not ids:
        return {"evaluated": 0, "created": 0, "errors": []}
    return evaluate_groups_for_shipment_ids(database, alerts_repo, ids)


def evaluate_groups_after_tracking_sync(
    database: Database,
    shipment_nos: list[str],
    log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """轨迹同步后：对本次有更新的运单所在分组重新评估提醒。"""
    nos = list(dict.fromkeys(n.strip() for n in shipment_nos if n and n.strip()))
    if not nos:
        return {
            "groupAlertsEvaluated": 0,
            "groupAlertsCreated": 0,
            "groupAlertsErrors": [],
        }
    alerts_repo = ShipmentGroupAlertsRepository(database)
    result = evaluate_groups_for_shipment_nos(database, alerts_repo, nos)
    evaluated = int(result.get("evaluated") or 0)
    created = int(result.get("created") or 0)
    errors = list(result.get("errors") or [])
    if log:
        if created:
            log(f"[分组提醒] 轨迹同步后评估 {evaluated} 个分组，新增 {created} 条提醒")
        elif evaluated:
            log(f"[分组提醒] 轨迹同步后评估 {evaluated} 个分组，无新提醒")
        for err in errors[:5]:
            msg = err.get("message") if isinstance(err, dict) else str(err)
            log(f"[分组提醒] 评估失败：{msg}")
    return {
        "groupAlertsEvaluated": evaluated,
        "groupAlertsCreated": created,
        "groupAlertsErrors": errors,
    }
