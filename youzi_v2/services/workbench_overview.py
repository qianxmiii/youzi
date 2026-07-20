"""工作台首页聚合：今日重点 / 待办 / 近期到港 / 运输概览。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str, normalize_tracking_time
from youzi_v2.db.port_subscriptions_table import PortSubscriptionsRepository
from youzi_v2.db.shipment_payment_followups_repository import (
    ShipmentPaymentFollowupsRepository,
)
from youzi_v2.db.shipment_sla import RISK_SEVERE_OVERDUE, RISK_OVERDUE
from youzi_v2.db.shipment_sla_alerts_repository import ShipmentSlaAlertsRepository
from youzi_v2.db.shipment_tracking_time_candidates_repository import (
    ShipmentTrackingTimeCandidatesRepository,
)
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.services.maritime_alerts import build_maritime_alerts_overview
from youzi_v2.services.payment_reminder_rules import REMINDER_OVERDUE, REMINDER_TODAY


def _parse_dt(raw: str | None) -> datetime | None:
    text = normalize_tracking_time(raw)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19] if fmt != "%Y-%m-%d" else text[:10], fmt)
        except ValueError:
            continue
    return None

SHIPMENTS_TABLE = "shipments"
_TRACKING_STALE_DAYS = 3
_TODO_FETCH_CAP = 80

_KIND_LABELS = {
    "exception": "异常",
    "payment": "待催款",
    "tracking_review": "轨迹审批",
}

_RISK_LABELS = {
    "severe_overdue": "严重超时",
    "overdue": "已超时",
    "warning_soon": "即将超时",
}


def _week_bounds(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _safe_module(builder, *, empty: dict[str, Any]) -> dict[str, Any]:
    try:
        data = builder()
        # data 可带部分源失败的 error；放在末尾以免被覆盖
        return {**empty, "available": True, "error": None, **data}
    except Exception as exc:  # noqa: BLE001 — 模块隔离，勿向上抛
        return {**empty, "available": False, "error": str(exc) or "暂不可用"}


def _build_focus(
    *,
    database: Database,
    sla_repo: ShipmentSlaAlertsRepository,
    payment_repo: ShipmentPaymentFollowupsRepository,
    shipments_repo: ShipmentsRepository,
) -> dict[str, Any]:
    pending_exceptions = 0
    pending_collections = 0
    pending_tracking_reviews = 0
    arriving_soon = 0
    errors: list[str] = []

    try:
        pending_exceptions = int(sla_repo.summary_counts().get("pendingOpen") or 0)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"异常:{exc}")

    try:
        pending_collections = int(payment_repo.reminder_summary().get("todoCount") or 0)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"催款:{exc}")

    try:
        pending_tracking_reviews = int(
            shipments_repo.tracking_freshness_stats().get("pendingTrackingTimeReview") or 0
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"审批:{exc}")

    try:
        maritime = build_maritime_alerts_overview(database)
        arriving_soon = int((maritime.get("counts") or {}).get("arrivingSoon") or 0)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"到港:{exc}")

    if len(errors) >= 4:
        raise RuntimeError("；".join(errors))

    return {
        "pendingExceptions": pending_exceptions,
        "pendingCollections": pending_collections,
        "pendingTrackingReviews": pending_tracking_reviews,
        "arrivingSoon": arriving_soon,
        "error": "；".join(errors) if errors else None,
    }


def _exception_priority(alert: dict[str, Any]) -> tuple[int, str, str]:
    risk = (alert.get("riskLevel") or "").strip()
    if risk == RISK_SEVERE_OVERDUE:
        return 1, "severe", _RISK_LABELS.get(risk, "严重超时")
    if risk == RISK_OVERDUE:
        return 4, "high", _RISK_LABELS.get(risk, "已超时")
    return 4, "normal", _RISK_LABELS.get(risk, "待处理异常")


def _payment_priority(item: dict[str, Any]) -> tuple[int, str, str]:
    rt = (item.get("reminderType") or "").strip()
    if rt in (REMINDER_OVERDUE, REMINDER_TODAY):
        label = "已逾期催款" if rt == REMINDER_OVERDUE else "当天催款"
        return 2, "high", label
    return 5, "normal", item.get("reminderTypeLabel") or "待催款"


def _tracking_priority(item: dict[str, Any], *, now: datetime) -> tuple[int, str, str]:
    updated = _parse_dt(item.get("updatedTime") or item.get("createdTime"))
    stale = False
    if updated is not None:
        stale = (now - updated) >= timedelta(days=_TRACKING_STALE_DAYS)
    if stale:
        return 3, "high", "久未处理审批"
    return 5, "normal", "轨迹审批"


def _todo_sort_key(item: dict[str, Any]) -> tuple:
    return (
        int(item.get("priority") or 99),
        -int(item.get("overdueDays") or 0),
        item.get("triggerTime") or "9999",
        item.get("updatedTime") or "9999",
    )


def _merge_todos(
    raw: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    by_shipment: dict[str, list[dict[str, Any]]] = defaultdict(list)
    orphans: list[dict[str, Any]] = []
    for item in raw:
        sid = (item.get("shipmentId") or "").strip()
        if sid:
            by_shipment[sid].append(item)
        else:
            orphans.append(item)

    merged: list[dict[str, Any]] = []
    for sid, parts in by_shipment.items():
        parts.sort(key=_todo_sort_key)
        top = parts[0]
        kinds = []
        labels = []
        seen_kind = set()
        for p in parts:
            kind = p["kind"]
            if kind not in seen_kind:
                seen_kind.add(kind)
                kinds.append(kind)
                labels.append(p.get("kindLabel") or _KIND_LABELS.get(kind, kind))
        n = len(parts)
        if n == 1:
            title = top.get("title") or labels[0]
            summary = top.get("summary") or ""
        else:
            title = f"{n} 项待处理：{'、'.join(labels)}"
            summary = "；".join(
                (p.get("summary") or p.get("kindLabel") or "") for p in parts if p.get("summary")
            )
        merged.append(
            {
                "id": f"ship:{sid}",
                "kinds": kinds,
                "priority": top["priority"],
                "severity": top.get("severity") or "normal",
                "shipmentId": sid,
                "shipmentNo": top.get("shipmentNo") or "",
                "customer": top.get("customer") or "",
                "title": title,
                "summary": summary,
                "href": top.get("href") or "",
                "overdueDays": max(int(p.get("overdueDays") or 0) for p in parts),
                "triggerTime": top.get("triggerTime"),
                "updatedTime": top.get("updatedTime"),
            }
        )

    for item in orphans:
        merged.append(
            {
                "id": item.get("id") or item.get("kind", "todo"),
                "kinds": [item["kind"]],
                "priority": item["priority"],
                "severity": item.get("severity") or "normal",
                "shipmentId": item.get("shipmentId"),
                "shipmentNo": item.get("shipmentNo") or "",
                "customer": item.get("customer") or "",
                "title": item.get("title") or "",
                "summary": item.get("summary") or "",
                "href": item.get("href") or "",
                "overdueDays": int(item.get("overdueDays") or 0),
                "triggerTime": item.get("triggerTime"),
                "updatedTime": item.get("updatedTime"),
            }
        )

    merged.sort(key=_todo_sort_key)
    return merged[: max(1, limit)]


def _build_todos(
    *,
    sla_repo: ShipmentSlaAlertsRepository,
    payment_repo: ShipmentPaymentFollowupsRepository,
    candidates_repo: ShipmentTrackingTimeCandidatesRepository,
    todo_limit: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now()
    fetch = min(_TODO_FETCH_CAP, max(todo_limit * 4, 24))
    raw: list[dict[str, Any]] = []

    alerts = sla_repo.list_alerts(scope="todo", limit=fetch, offset=0).get("items") or []
    for alert in alerts:
        priority, severity, kind_label = _exception_priority(alert)
        sn = (alert.get("shipmentNo") or "").strip()
        raw.append(
            {
                "id": f"exc:{alert.get('id')}",
                "kind": "exception",
                "kindLabel": kind_label,
                "priority": priority,
                "severity": severity,
                "shipmentId": alert.get("shipmentId"),
                "shipmentNo": sn,
                "customer": alert.get("customer") or "",
                "title": kind_label,
                "summary": (alert.get("exceptionNameZh") or alert.get("note") or kind_label),
                "href": f"/shipment-exceptions?status=open&shipmentNo={quote(sn)}"
                if sn
                else "/shipment-exceptions?status=open",
                "overdueDays": int(alert.get("overdueDays") or 0),
                "triggerTime": alert.get("createdTime") or alert.get("dueDate"),
                "updatedTime": alert.get("updatedTime"),
            }
        )

    payments = payment_repo.list_reminders(scope="todo", limit=fetch, offset=0).get("items") or []
    for pay in payments:
        priority, severity, kind_label = _payment_priority(pay)
        sn = (pay.get("shipmentNo") or "").strip()
        raw.append(
            {
                "id": f"pay:{pay.get('shipmentId')}",
                "kind": "payment",
                "kindLabel": kind_label,
                "priority": priority,
                "severity": severity,
                "shipmentId": pay.get("shipmentId"),
                "shipmentNo": sn,
                "customer": pay.get("customer") or "",
                "title": kind_label,
                "summary": pay.get("reminderTypeLabel") or kind_label,
                "href": "/shipments/payment-reminders?scope=todo",
                "overdueDays": int(pay.get("overdueDays") or 0),
                "triggerTime": pay.get("dueDate") or pay.get("reminderDate"),
                "updatedTime": pay.get("lastFollowupTime") or pay.get("dueDate"),
            }
        )

    reviews = candidates_repo.list_pending_reviews(limit=fetch, offset=0).get("items") or []
    for rev in reviews:
        priority, severity, kind_label = _tracking_priority(rev, now=now)
        sn = (rev.get("shipmentNo") or "").strip()
        field = (rev.get("fieldName") or "").strip()
        raw.append(
            {
                "id": f"trk:{rev.get('id')}",
                "kind": "tracking_review",
                "kindLabel": kind_label,
                "priority": priority,
                "severity": severity,
                "shipmentId": rev.get("shipmentId"),
                "shipmentNo": sn,
                "customer": "",
                "title": kind_label,
                "summary": f"{field} 待审批" if field else "轨迹时间待审批",
                "href": "/approvals/tracking-time?status=pending_review",
                "overdueDays": 0,
                "triggerTime": rev.get("createdTime") or rev.get("updatedTime"),
                "updatedTime": rev.get("updatedTime"),
            }
        )

    return {"items": _merge_todos(raw, limit=todo_limit)}


def _day_group_for_eta(eta_dt: datetime, *, today: date) -> str:
    eta_day = eta_dt.date()
    if eta_day == today:
        return "today"
    if eta_day == today + timedelta(days=1):
        return "tomorrow"
    return "later"


def _build_arrivals(
    *,
    database: Database,
    arrival_limit: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now()
    today = now.date()
    window_start = datetime(today.year, today.month, today.day)
    window_end = window_start + timedelta(days=4)

    with database.lock:
        rows = database.conn.execute(
            f"""
            SELECT shipment_no, customer, vessel_voyage, eta, ata,
                   destination_port_code, status_code
            FROM {SHIPMENTS_TABLE}
            WHERE TRIM(COALESCE(eta, '')) != ''
              AND (ata IS NULL OR TRIM(ata) = '')
              AND UPPER(TRIM(COALESCE(status_code, ''))) NOT IN ('CANCELLED', 'CANCELED')
            ORDER BY datetime(eta) ASC
            LIMIT 3000
            """
        ).fetchall()

    subscribed_names: set[str] = set()
    try:
        port_repo = PortSubscriptionsRepository(database)
        # 订阅挂靠的港口名，用于「订阅港」角标
        with database.lock:
            sub_rows = database.conn.execute(
                """
                SELECT DISTINCT TRIM(port_name) AS port_name
                FROM port_subscriptions
                WHERE TRIM(COALESCE(port_name, '')) != ''
                """
            ).fetchall()
        subscribed_names = {
            (r["port_name"] or "").strip().lower() for r in sub_rows if r["port_name"]
        }
    except Exception:  # noqa: BLE001
        subscribed_names = set()

    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        eta_raw = normalize_tracking_time(row["eta"])
        eta_dt = _parse_dt(eta_raw)
        if eta_dt is None:
            continue
        if not (window_start <= eta_dt < window_end):
            continue
        vessel = (row["vessel_voyage"] or "").strip() or "—"
        dest = (row["destination_port_code"] or "").strip()
        eta_key = eta_raw or ""
        key = (vessel, dest, eta_key)
        if key not in buckets:
            buckets[key] = {
                "dayGroup": _day_group_for_eta(eta_dt, today=today),
                "vesselVoyage": vessel,
                "destinationPortCode": dest,
                "eta": eta_raw or None,
                "shipmentCount": 0,
                "isSubscribedPort": dest.lower() in subscribed_names if dest else False,
                "href": (
                    f"/shipments?vesselVoyage={quote(vessel)}"
                    if vessel and vessel != "—"
                    else "/vessel-schedules?maritimeStatus=arriving_soon"
                ),
                "_eta_dt": eta_dt,
            }
        buckets[key]["shipmentCount"] += 1

    items = sorted(
        buckets.values(),
        key=lambda x: (
            {"today": 0, "tomorrow": 1, "later": 2}.get(x["dayGroup"], 9),
            x["_eta_dt"],
            x["vesselVoyage"],
        ),
    )
    for item in items:
        item.pop("_eta_dt", None)

    return {"items": items[: max(1, arrival_limit)]}


def _build_overview(*, database: Database, today: date | None = None) -> dict[str, Any]:
    monday, sunday = _week_bounds(today)
    monday_s = monday.isoformat()
    sunday_s = sunday.isoformat()

    with database.lock:
        in_transit = int(
            database.conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {SHIPMENTS_TABLE}
                WHERE UPPER(TRIM(COALESCE(status_code, ''))) = 'IN_TRANSIT'
                  AND (delivered_time IS NULL OR TRIM(delivered_time) = '')
                """
            ).fetchone()["c"]
            or 0
        )
        inspection = int(
            database.conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {SHIPMENTS_TABLE}
                WHERE exception_code IS NOT NULL
                  AND TRIM(exception_code) != ''
                  AND UPPER(TRIM(exception_code)) = 'INSPECTION'
                """
            ).fetchone()["c"]
            or 0
        )
        arrived_unsigned = int(
            database.conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {SHIPMENTS_TABLE}
                WHERE ata IS NOT NULL AND TRIM(ata) != ''
                  AND (delivered_time IS NULL OR TRIM(delivered_time) = '')
                  AND UPPER(TRIM(COALESCE(status_code, ''))) NOT IN (
                    'CANCELLED', 'CANCELED', 'DELIVERED'
                  )
                """
            ).fetchone()["c"]
            or 0
        )
        delivered_this_week = int(
            database.conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {SHIPMENTS_TABLE}
                WHERE delivered_time IS NOT NULL AND TRIM(delivered_time) != ''
                  AND date(delivered_time) >= date(?)
                  AND date(delivered_time) <= date(?)
                """,
                (monday_s, sunday_s),
            ).fetchone()["c"]
            or 0
        )

    return {
        "inTransit": in_transit,
        "inspection": inspection,
        "arrivedUnsigned": arrived_unsigned,
        "deliveredThisWeek": delivered_this_week,
    }


def build_workbench_overview(
    database: Database,
    *,
    todo_limit: int = 8,
    arrival_limit: int = 6,
) -> dict[str, Any]:
    """聚合首页四模块；单模块失败不影响其余模块。"""
    todo_limit = max(1, min(int(todo_limit or 8), 20))
    arrival_limit = max(1, min(int(arrival_limit or 6), 20))

    sla_repo = ShipmentSlaAlertsRepository(database)
    payment_repo = ShipmentPaymentFollowupsRepository(database)
    shipments_repo = ShipmentsRepository(database)
    candidates_repo = ShipmentTrackingTimeCandidatesRepository(database)

    focus_empty = {
        "pendingExceptions": 0,
        "pendingCollections": 0,
        "pendingTrackingReviews": 0,
        "arrivingSoon": 0,
    }
    focus = _safe_module(
        lambda: _build_focus(
            database=database,
            sla_repo=sla_repo,
            payment_repo=payment_repo,
            shipments_repo=shipments_repo,
        ),
        empty=focus_empty,
    )
    # 部分 focus 源失败时仍 available=true，但透传 error 供排查
    if focus.get("available") and focus.get("error"):
        pass

    todos = _safe_module(
        lambda: _build_todos(
            sla_repo=sla_repo,
            payment_repo=payment_repo,
            candidates_repo=candidates_repo,
            todo_limit=todo_limit,
        ),
        empty={"items": []},
    )
    arrivals = _safe_module(
        lambda: _build_arrivals(
            database=database,
            arrival_limit=arrival_limit,
        ),
        empty={"items": []},
    )
    overview = _safe_module(
        lambda: _build_overview(database=database),
        empty={
            "inTransit": 0,
            "inspection": 0,
            "arrivedUnsigned": 0,
            "deliveredThisWeek": 0,
        },
    )

    return {
        "generatedAt": now_str(),
        "focus": focus,
        "todos": todos,
        "arrivals": arrivals,
        "overview": overview,
    }
