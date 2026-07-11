"""从 DPS 同步运单至本地 shipments 表。"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from ..db.shipments_repository import ShipmentsRepository
from .shipment_dps_mapper import dps_row_to_shipment
from .shipment_dps_sync_fields import filter_dps_payload, get_dps_sync_fields_config
from .shipment_dps_sync_schedule import should_run_scheduled_dps_sync
from .shipment_dps_sync_settings import (
    get_shipment_dps_sync_settings,
    record_shipment_dps_sync_finished,
)
from .shipment_query_config import (
    normalize_shipment_nos,
    query_shipments_by_order,
    query_shipments_by_person,
    resolve_transit_time_range,
    shipment_odd,
)

LogFn = Callable[[str], None]

_lock = threading.Lock()
_BY_ORDER_CHUNK_SIZE = 50
_MAX_BY_ORDER_NOS = 200


def _maybe_backfill_payment_status(
    filtered: dict[str, Any],
    *,
    payload: dict[str, Any],
    existing: dict[str, Any] | None,
    is_new: bool,
) -> dict[str, Any]:
    """DPS 付款状态：空值回填；本地未付款时允许升为已付款；本地已付款不覆盖。"""
    if is_new or existing is None:
        return filtered
    dps_ps = (payload.get("payment_status") or "").strip().upper()
    if dps_ps not in ("PAID", "UNPAID"):
        return filtered
    local_ps = (existing.get("paymentStatus") or "").strip().upper()
    if local_ps == "PAID":
        return filtered
    if not local_ps or (local_ps == "UNPAID" and dps_ps == "PAID"):
        return {**filtered, "payment_status": dps_ps}
    return filtered


def _upsert_dps_rows(
    shipments_repo: ShipmentsRepository,
    rows: list[Any],
    *,
    log: LogFn | None = None,
) -> dict[str, Any]:
    database = shipments_repo._database
    field_cfg = get_dps_sync_fields_config()
    created = 0
    updated = 0
    unchanged = 0
    failed = 0
    errors: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            failed += 1
            continue
        payload = dps_row_to_shipment(row)
        if not payload:
            failed += 1
            continue
        shipment_no = str(payload.get("shipment_no") or "").strip()
        try:
            existing = shipments_repo.get_by_shipment_no(shipment_no)
            is_new = existing is None
            filtered = filter_dps_payload(payload, is_new=is_new, config=field_cfg)
            filtered = _maybe_backfill_payment_status(
                filtered,
                payload=payload,
                existing=existing,
                is_new=is_new,
            )
            before_id = None if is_new else existing["id"]
            result_row, was_created = shipments_repo.upsert_by_shipment_no(filtered)
            if was_created:
                created += 1
            elif before_id and result_row.get("updatedTime") == existing.get(
                "updatedTime"
            ):
                unchanged += 1
            else:
                updated += 1
        except Exception as exc:
            failed += 1
            sn = payload.get("shipment_no") or "?"
            if len(errors) < 20:
                errors.append(f"{sn}: {exc}")
            if log:
                log(f"[DPS运单同步] 失败 {sn}: {exc}")

    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "failed": failed,
        "errors": errors,
    }


def _chunk_shipment_nos(shipment_nos: list[str], size: int) -> list[list[str]]:
    return [shipment_nos[i : i + size] for i in range(0, len(shipment_nos), size)]


def run_shipment_dps_sync_by_order(
    shipments_repo: ShipmentsRepository,
    config_path: Path,
    shipment_nos: list[str] | str,
    *,
    log: LogFn | None = None,
) -> dict[str, Any]:
    """按运单号从 shipment_queryByOrder 拉取并 upsert。"""

    def out(msg: str) -> None:
        if log:
            log(msg)

    nos = normalize_shipment_nos(shipment_nos)
    if not nos:
        return {
            "skipped": True,
            "reason": "运单号不能为空",
            "total": 0,
            "created": 0,
            "updated": 0,
            "failed": 0,
        }
    if len(nos) > _MAX_BY_ORDER_NOS:
        return {
            "skipped": True,
            "reason": f"单次最多 {_MAX_BY_ORDER_NOS} 个运单号",
            "total": 0,
            "created": 0,
            "updated": 0,
            "failed": 0,
        }

    if not _lock.acquire(blocking=False):
        out("[DPS运单同步] 跳过：上一轮仍在进行")
        return {
            "skipped": True,
            "reason": "DPS 运单同步进行中",
            "total": 0,
            "created": 0,
            "updated": 0,
            "failed": 0,
        }

    try:
        out(f"[DPS运单同步] 按单号开始，共 {len(nos)} 个")
        all_rows: list[dict[str, Any]] = []
        pages = 0
        remote_total = 0

        for chunk in _chunk_shipment_nos(nos, _BY_ORDER_CHUNK_SIZE):
            parsed, err = query_shipments_by_order(chunk, config_path)
            if err:
                out(f"[DPS运单同步] 失败：{err}")
                return {
                    "skipped": False,
                    "error": err,
                    "total": 0,
                    "created": 0,
                    "updated": 0,
                    "failed": 0,
                }
            assert parsed is not None
            chunk_rows = [r for r in (parsed.get("rows") or []) if isinstance(r, dict)]
            all_rows.extend(chunk_rows)
            pages += int(parsed.get("pages") or 0)
            remote_total += int(parsed.get("total") or len(chunk_rows))

        returned_nos = {shipment_odd(r) for r in all_rows if shipment_odd(r)}
        not_found_nos = [n for n in nos if n not in returned_nos]

        stats = _upsert_dps_rows(shipments_repo, all_rows, log=log)
        out(
            f"[DPS运单同步] 按单号完成 remote={remote_total} 写入="
            f"{stats['created'] + stats['updated']} 新增={stats['created']} "
            f"更新={stats['updated']} 无变化={stats['unchanged']} 失败={stats['failed']} "
            f"未返回={len(not_found_nos)}"
        )
        return {
            "skipped": False,
            "remoteTotal": remote_total,
            "total": len(all_rows),
            "notFound": len(not_found_nos),
            "notFoundNos": not_found_nos[:50],
            "pages": pages,
            **stats,
        }
    finally:
        _lock.release()


def run_shipment_dps_sync_batch(
    shipments_repo: ShipmentsRepository,
    config_path: Path,
    *,
    transit_time_start: str | None = None,
    transit_time_end: str | None = None,
    force: bool = False,
    trigger: str = "manual",
    log: LogFn | None = None,
) -> dict[str, Any]:
    database = shipments_repo._database

    def out(msg: str) -> None:
        if log:
            log(msg)

    if not force:
        ok, reason = should_run_scheduled_dps_sync(database)
        if not ok:
            out(f"[DPS运单同步] 跳过：{reason}")
            return {
                "skipped": True,
                "reason": reason,
                "total": 0,
                "created": 0,
                "updated": 0,
                "failed": 0,
            }

    if not _lock.acquire(blocking=False):
        out("[DPS运单同步] 跳过：上一轮仍在进行")
        return {
            "skipped": True,
            "reason": "DPS 运单同步进行中",
            "total": 0,
            "created": 0,
            "updated": 0,
            "failed": 0,
        }

    settings = get_shipment_dps_sync_settings(database)
    start, end = resolve_transit_time_range(
        transit_time_start if transit_time_start is not None else settings.transit_time_start,
        transit_time_end if transit_time_end is not None else settings.transit_time_end,
    )

    try:
        out(f"[DPS运单同步] 开始 {start} ~ {end}（触发：{trigger}）")
        parsed, err = query_shipments_by_person(
            config_path,
            transit_time_start=start,
            transit_time_end=end,
        )
        if err:
            out(f"[DPS运单同步] 失败：{err}")
            return {
                "skipped": False,
                "error": err,
                "transitTimeStart": start,
                "transitTimeEnd": end,
                "total": 0,
                "created": 0,
                "updated": 0,
                "failed": 0,
            }
        assert parsed is not None
        rows = list(parsed.get("rows") or [])
        total = int(parsed.get("total") or len(rows))
        stats = _upsert_dps_rows(shipments_repo, rows, log=log)
        out(
            f"[DPS运单同步] 完成 remote={total} 写入={stats['created'] + stats['updated']} "
            f"新增={stats['created']} 更新={stats['updated']} "
            f"无变化={stats['unchanged']} 失败={stats['failed']}"
        )
        if trigger == "scheduled" or force:
            record_shipment_dps_sync_finished(database)
        return {
            "skipped": False,
            "transitTimeStart": start,
            "transitTimeEnd": end,
            "remoteTotal": total,
            "total": len(rows),
            "pages": int(parsed.get("pages") or 0),
            **stats,
        }
    finally:
        _lock.release()
