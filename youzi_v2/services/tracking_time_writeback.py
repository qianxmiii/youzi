"""根据内部轨迹重算候选时间并回写运单字段。"""

from __future__ import annotations

from typing import Any, Callable

from ..db.connection import Database
from ..db.datetime_util import normalize_tracking_time, now_str
from ..db.internal_tracking_logs_table import TABLE_NAME as INTERNAL_TRACKING_TABLE
from ..db.shipment_tracking_time_candidates_repository import (
    ShipmentTrackingTimeCandidatesRepository,
)
from ..db.shipment_tracking_time_candidates_table import TABLE_NAME as CANDIDATES_TABLE
from ..db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from ..tracking_time_parser import (
    ParsedTimeCandidate,
    build_time_candidates,
    tracks_from_rows,
)

LogFn = Callable[[str], None]

AUTO_APPLY_FIELDS = frozenset(
    {"etd", "eta", "atd", "ata", "expected_delivery_time", "warehouse_entry_time"},
)

SHIPMENT_COLUMN_MAP = {
    "etd": "etd",
    "eta": "eta",
    "atd": "atd",
    "ata": "ata",
    "expected_delivery_time": "expected_delivery_time",
    "warehouse_entry_time": "warehouse_entry_time",
    "signed_time": "delivered_time",
}

SOURCE_EXPECTED = "expected_delivery_time"
SOURCE_SIGNED = "signed_track_time"

REVIEW_ACTIONS = frozenset(
    {"use_expected_delivery", "use_signed_track", "manual", "reject", "approve"},
)


def same_calendar_date(left: str, right: str) -> bool:
    a = normalize_tracking_time(left)
    b = normalize_tracking_time(right)
    if not a or not b:
        return False
    return a[:10] == b[:10]


def _signed_review_reason(signed_value: str, expected_value: str) -> str:
    signed_date = normalize_tracking_time(signed_value)[:10]
    expected_date = normalize_tracking_time(expected_value)[:10]
    return (
        f"签收节点事件日期 {signed_date} 与预计送仓日期 {expected_date} 不一致，"
        f"需确认是否采用预计送仓时间作为签收时间"
    )


def _load_shipment(conn, shipment_id: str | None = None, shipment_no: str | None = None):
    if shipment_id:
        return conn.execute(
            f"SELECT * FROM {SHIPMENTS_TABLE} WHERE id = ?",
            (shipment_id.strip(),),
        ).fetchone()
    if shipment_no:
        return conn.execute(
            f"SELECT * FROM {SHIPMENTS_TABLE} WHERE shipment_no = ?",
            (shipment_no.strip(),),
        ).fetchone()
    return None


def _load_internal_tracks(conn, shipment_no: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT id, shipment_no, tracking_time, tracking_desc, created_time
        FROM {INTERNAL_TRACKING_TABLE}
        WHERE shipment_no = ?
        ORDER BY datetime(tracking_time) ASC, datetime(created_time) ASC, id ASC
        """,
        (shipment_no.strip(),),
    ).fetchall()
    return [dict(r) for r in rows]


def _apply_shipment_fields(
    conn,
    shipment_id: str,
    updates: dict[str, str],
) -> None:
    if not updates:
        return
    sets: list[str] = ["updated_time = ?"]
    params: list[Any] = [now_str()]
    for key, value in updates.items():
        sets.append(f"{key} = ?")
        params.append(value)
    params.append(shipment_id)
    conn.execute(
        f"""
        UPDATE {SHIPMENTS_TABLE} SET {', '.join(sets)}
        WHERE id = ?
          AND (payment_status IS NULL OR UPPER(TRIM(payment_status)) != 'PAID')
        """,
        params,
    )


def _upsert_signed_candidate(
    repo: ShipmentTrackingTimeCandidatesRepository,
    shipment_id: str,
    *,
    recommended: ParsedTimeCandidate,
    compare: ParsedTimeCandidate,
    review_status: str,
    review_reason: str,
    applied: bool,
) -> None:
    repo.upsert_candidate(
        shipment_id,
        field_name="signed_time",
        candidate_value=recommended.candidate_value,
        compare_value=compare.candidate_value,
        recommended_source=SOURCE_EXPECTED,
        compare_source=SOURCE_SIGNED,
        source_track_id=recommended.source_track_id,
        source_track_time=recommended.source_track_time,
        source_track_desc=recommended.source_track_desc,
        compare_source_track_id=compare.source_track_id,
        compare_source_track_time=compare.source_track_time,
        compare_source_track_desc=compare.source_track_desc,
        confidence=recommended.confidence,
        review_status=review_status,
        review_reason=review_reason,
        applied=applied,
    )


def _apply_signed_time_with_review(
    repo: ShipmentTrackingTimeCandidatesRepository,
    shipment_id: str,
    *,
    signed: ParsedTimeCandidate,
    expected: ParsedTimeCandidate | None,
    shipment_updates: dict[str, str],
    applied_fields: list[str],
    pending_review: list[str],
) -> None:
    if expected is None or not expected.candidate_value:
        repo.upsert_candidate(
            shipment_id,
            field_name="signed_time",
            candidate_value=signed.candidate_value,
            compare_value="",
            recommended_source=SOURCE_SIGNED,
            compare_source="",
            source_track_id=signed.source_track_id,
            source_track_time=signed.source_track_time,
            source_track_desc=signed.source_track_desc,
            confidence=signed.confidence,
            review_status="auto_confirmed",
            review_reason="",
            applied=True,
        )
        shipment_updates[SHIPMENT_COLUMN_MAP["signed_time"]] = signed.candidate_value
        applied_fields.append("signed_time")
        return

    if same_calendar_date(signed.candidate_value, expected.candidate_value):
        _upsert_signed_candidate(
            repo,
            shipment_id,
            recommended=expected,
            compare=signed,
            review_status="auto_confirmed",
            review_reason="",
            applied=True,
        )
        shipment_updates[SHIPMENT_COLUMN_MAP["signed_time"]] = expected.candidate_value
        applied_fields.append("signed_time")
        return

    _upsert_signed_candidate(
        repo,
        shipment_id,
        recommended=expected,
        compare=signed,
        review_status="pending_review",
        review_reason=_signed_review_reason(signed.candidate_value, expected.candidate_value),
        applied=False,
    )
    pending_review.append("signed_time")


def recalculate_for_shipment(
    database: Database,
    *,
    shipment_id: str | None = None,
    shipment_no: str | None = None,
    candidates_repo: ShipmentTrackingTimeCandidatesRepository | None = None,
    log: LogFn | None = None,
) -> dict[str, Any]:
    repo = candidates_repo or ShipmentTrackingTimeCandidatesRepository(database)
    applied_fields: list[str] = []
    pending_review: list[str] = []

    with database.lock:
        shipment = _load_shipment(database.conn, shipment_id, shipment_no)
        if shipment is None:
            return {"found": False, "applied": [], "pendingReview": []}

        sid = str(shipment["id"])
        sn = str(shipment["shipment_no"])
        track_rows = _load_internal_tracks(database.conn, sn)
        tracks = tracks_from_rows(track_rows)
        candidates = build_time_candidates(
            tracks,
            shipment_created_time=str(shipment["created_time"] or ""),
        )

        shipment_updates: dict[str, str] = {}
        expected = candidates.get("expected_delivery_time")

        for field_name, candidate in candidates.items():
            if candidate is None or not candidate.candidate_value:
                repo.delete_field(sid, field_name)
                continue

            if field_name == "signed_time":
                _apply_signed_time_with_review(
                    repo,
                    sid,
                    signed=candidate,
                    expected=expected,
                    shipment_updates=shipment_updates,
                    applied_fields=applied_fields,
                    pending_review=pending_review,
                )
                continue

            if field_name in AUTO_APPLY_FIELDS:
                repo.upsert_candidate(
                    sid,
                    field_name=field_name,
                    candidate_value=candidate.candidate_value,
                    source_track_id=candidate.source_track_id,
                    source_track_time=candidate.source_track_time,
                    source_track_desc=candidate.source_track_desc,
                    confidence=candidate.confidence,
                    review_status="auto_confirmed",
                    review_reason="",
                    applied=True,
                )
                shipment_updates[SHIPMENT_COLUMN_MAP[field_name]] = candidate.candidate_value
                applied_fields.append(field_name)

        _apply_shipment_fields(database.conn, sid, shipment_updates)
        database.conn.commit()

    if "delivered_time" in shipment_updates and (shipment_updates.get("delivered_time") or "").strip():
        from .shipment_sla_scan import maybe_resolve_alerts_after_delivery

        maybe_resolve_alerts_after_delivery(
            database,
            sid,
            shipment_no=sn,
            log=log,
        )

    if log and applied_fields:
        log(f"[时间回写] {sn} 已回写 {', '.join(applied_fields)}")
    if log and pending_review:
        log(f"[时间回写] {sn} 签收时间待审批")

    return {
        "found": True,
        "shipmentId": sid,
        "shipmentNo": sn,
        "applied": applied_fields,
        "pendingReview": pending_review,
    }


def recalculate_for_shipment_nos(
    database: Database,
    shipment_nos: list[str],
    *,
    log: LogFn | None = None,
) -> dict[str, Any]:
    nos = list(dict.fromkeys(n.strip() for n in shipment_nos if n and n.strip()))
    if not nos:
        return {"processed": 0, "appliedTotal": 0, "pendingReviewTotal": 0}
    repo = ShipmentTrackingTimeCandidatesRepository(database)
    applied_total = 0
    pending_total = 0
    for sn in nos:
        result = recalculate_for_shipment(
            database,
            shipment_no=sn,
            candidates_repo=repo,
            log=log,
        )
        applied_total += len(result.get("applied") or [])
        pending_total += len(result.get("pendingReview") or [])
    return {
        "processed": len(nos),
        "appliedTotal": applied_total,
        "pendingReviewTotal": pending_total,
    }


def list_shipment_nos_with_internal_tracks(database: Database) -> list[str]:
    with database.lock:
        rows = database.conn.execute(
            f"""
            SELECT DISTINCT shipment_no
            FROM {INTERNAL_TRACKING_TABLE}
            WHERE shipment_no IS NOT NULL AND TRIM(shipment_no) != ''
            ORDER BY shipment_no
            """
        ).fetchall()
    return [str(r[0]).strip() for r in rows if r[0]]


def recalculate_all_with_internal_tracks(
    database: Database,
    *,
    log: LogFn | None = None,
    progress_every: int = 100,
) -> dict[str, Any]:
    """对有内部轨迹的运单全量重算时间候选并回写。"""
    nos = list_shipment_nos_with_internal_tracks(database)
    if log:
        log(f"[时间回写] 开始批量重算，共 {len(nos)} 票有内部轨迹")
    repo = ShipmentTrackingTimeCandidatesRepository(database)
    applied_total = 0
    pending_total = 0
    found_total = 0
    for idx, sn in enumerate(nos, start=1):
        result = recalculate_for_shipment(
            database,
            shipment_no=sn,
            candidates_repo=repo,
            log=log,
        )
        if result.get("found"):
            found_total += 1
        applied_total += len(result.get("applied") or [])
        pending_total += len(result.get("pendingReview") or [])
        if log and progress_every > 0 and idx % progress_every == 0:
            log(f"[时间回写] 进度 {idx}/{len(nos)}")
    if log:
        log(
            f"[时间回写] 批量完成：处理 {len(nos)} 票，"
            f"命中运单 {found_total}，回写字段 {applied_total} 次，"
            f"待审批 {pending_total} 条"
        )
    return {
        "totalWithTracks": len(nos),
        "processed": len(nos),
        "found": found_total,
        "appliedTotal": applied_total,
        "pendingReviewTotal": pending_total,
    }


def approve_signed_time_candidate(
    database: Database,
    candidate_id: str,
    *,
    action: str,
    manual_value: str | None = None,
) -> dict[str, Any]:
    repo = ShipmentTrackingTimeCandidatesRepository(database)
    act = action.strip().lower()
    if act == "approve":
        act = "use_expected_delivery"
    if act not in REVIEW_ACTIONS:
        raise ValueError(
            "action 须为 use_expected_delivery、use_signed_track、manual 或 reject"
        )

    with database.lock:
        row = database.conn.execute(
            f"SELECT * FROM {CANDIDATES_TABLE} WHERE id = ?",
            (candidate_id.strip(),),
        ).fetchone()
        if row is None:
            raise KeyError(candidate_id)
        if str(row["field_name"]) != "signed_time":
            raise ValueError("仅支持签收时间候选审批")

        shipment_id = str(row["shipment_id"])

        if act == "reject":
            repo.mark_review(
                candidate_id,
                review_status="manual_rejected",
                review_reason="人工拒绝，维持现状",
                applied=False,
            )
            database.conn.commit()
            return {"action": "reject"}

        if act == "use_expected_delivery":
            value = (row["candidate_value"] or "").strip()
        elif act == "use_signed_track":
            keys = row.keys()
            value = (
                (row["compare_value"] if "compare_value" in keys else "") or ""
            ).strip()
        else:
            value = (manual_value or "").strip()

        if not value:
            raise ValueError("签收时间为空")
        value = normalize_tracking_time(value)
        repo.mark_review(
            candidate_id,
            review_status="manual_approved",
            review_reason="",
            applied=True,
        )
        database.conn.execute(
            f"""
            UPDATE {SHIPMENTS_TABLE}
            SET delivered_time = ?, updated_time = ?
            WHERE id = ?
              AND (payment_status IS NULL OR UPPER(TRIM(payment_status)) != 'PAID')
            """,
            (value, now_str(), shipment_id),
        )
        database.conn.commit()
        from .shipment_sla_scan import maybe_resolve_alerts_after_delivery

        maybe_resolve_alerts_after_delivery(database, shipment_id)
        return {"action": act, "deliveredTime": value}
