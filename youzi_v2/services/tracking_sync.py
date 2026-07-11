"""从物流 API 拉取运单轨迹并写入 internal_tracking_logs，更新运单内部摘要。

手动指定运单号：以接口返回全量覆盖本地轨迹（删除 DPS 已删节点）。
定时/全库同步：增量合并，只增不删。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..db.shipments_repository import ShipmentsRepository
from ..db.tracking_logs_repository import TrackingLogsRepository
from ..db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from ..internal_tracking import is_internal_no_tracking_desc
from .internal_batch_schedule import (
    is_internal_full_batch,
    record_internal_batch_finished,
    should_run_scheduled_internal_batch,
)
from .shipment_group_alerts import evaluate_groups_after_tracking_sync
from .shipment_sla_scan import evaluate_sla_after_tracking_sync
from .tracking_time_writeback import recalculate_for_shipment_nos
from .sync_log import make_sync_logger
from .logistics_tracking import (
    BATCH_SIZE,
    latest_from_logs,
    load_logistics_config,
    logs_from_api_item,
    query_logistics_api,
    shipment_no_from_api_item,
    status_code_from_api_item,
    status_label_from_api_item,
)

LogFn = Callable[[str], None]


def _delivered_time_for_status(
    status_code: str | None, latest_time: str
) -> str | None:
    """Legacy：签收时间改由 tracking_time_writeback 根据内部轨迹回写。"""
    return None


def sync_all_tracking(
    shipments_repo: ShipmentsRepository,
    tracking_repo: TrackingLogsRepository,
    config_path: Path,
    *,
    shipment_nos: list[str] | None = None,
    batch_size: int = BATCH_SIZE,
    jobs_repo: TrackingSyncJobsRepository | None = None,
    trigger: str = "manual",
    log: LogFn | None = None,
) -> dict[str, Any]:
    log_lines, out_log = make_sync_logger(log)

    if trigger == "scheduled" and is_internal_full_batch(shipment_nos):
        ok, skip_reason = should_run_scheduled_internal_batch(shipments_repo._database)
        if not ok:
            out_log(f"[轨迹同步] 跳过全库同步：{skip_reason}")
            return _skipped_internal_batch_result(log_lines, skip_reason or "")

    job_id: str | None = None
    if jobs_repo is not None:
        job_id = jobs_repo.create_job("internal", trigger)

    try:
        return _sync_all_tracking_body(
            shipments_repo,
            tracking_repo,
            config_path,
            shipment_nos=shipment_nos,
            batch_size=batch_size,
            jobs_repo=jobs_repo,
            job_id=job_id,
            trigger=trigger,
            log_lines=log_lines,
            out_log=out_log,
        )
    except Exception as exc:
        if jobs_repo is not None and job_id:
            jobs_repo.finish_job(
                job_id,
                status="failed",
                total_shipments=0,
                updated_shipments=0,
                new_log_count=0,
                errors=[str(exc)],
            )
        raise


def _sync_all_tracking_body(
    shipments_repo: ShipmentsRepository,
    tracking_repo: TrackingLogsRepository,
    config_path: Path,
    *,
    shipment_nos: list[str] | None,
    batch_size: int,
    jobs_repo: TrackingSyncJobsRepository | None,
    job_id: str | None,
    trigger: str,
    log_lines: list[str],
    out_log: LogFn,
) -> dict[str, Any]:
    config = load_logistics_config(config_path)
    base_url = config["base_url"]
    batch_size = BATCH_SIZE

    manual_scope = bool(shipment_nos)
    requested_nos = (
        len([s for s in shipment_nos if s and s.strip()]) if manual_scope else 0
    )
    tracking_list = shipments_repo.list_for_tracking_sync(
        shipment_nos,
        include_delivered=manual_scope,
    )
    total = len(tracking_list)
    excluded_not_in_transit = max(0, requested_nos - total) if manual_scope else 0
    if manual_scope:
        out_log(
            f"[轨迹同步] 指定 {requested_nos} 单，可同步 {total} 单（含已签收）"
            + (
                f"，未匹配 {excluded_not_in_transit} 单"
                if excluded_not_in_transit
                else ""
            )
        )
    if total == 0:
        out_log("[轨迹同步] 无待同步运单（已签收不参与），跳过")
        if jobs_repo is not None and job_id:
            jobs_repo.finish_job(
                job_id,
                status="success",
                total_shipments=0,
                updated_shipments=0,
                new_log_count=0,
            )
        return _empty_result(
            batch_size,
            log_lines,
            excluded_not_in_transit=excluded_not_in_transit,
            job_id=job_id,
        )

    out_log(f"[轨迹同步] 开始，base_url={base_url}")

    api_items, query_errors = query_logistics_api(
        tracking_list,
        base_url,
        batch_size=batch_size,
        log=out_log,
    )

    by_odd = {shipment_no_from_api_item(item): item for item in api_items}
    by_odd = {k: v for k, v in by_odd.items() if k}

    out_log(
        "[轨迹同步] 开始全量覆盖写入（以接口为准）…"
        if manual_scope
        else "[轨迹同步] 开始增量写入…"
    )

    updated = 0
    skipped = 0
    empty = 0
    log_count = 0
    not_found = 0
    updated_shipment_nos: list[str] = []

    for idx, row in enumerate(tracking_list, start=1):
        sn = row["tracking_number"]
        item = by_odd.get(sn)
        if item is None:
            not_found += 1
            continue

        api_status = status_code_from_api_item(item)
        stored_status = (row.get("status_code") or "").strip()
        status_label = status_label_from_api_item(item)

        logs = logs_from_api_item(item)
        if not logs:
            empty += 1
            if manual_scope:
                tracking_repo.replace_for_shipment(sn, [])
                shipments_repo.update_internal_tracking_summary(
                    sn,
                    "",
                    "",
                    log_count=0,
                    status_code=api_status,
                    delivered_time=_delivered_time_for_status(api_status, ""),
                )
                out_log(f"[轨迹同步] {sn} 接口无轨迹节点，已清空本地轨迹")
                updated += 1
                updated_shipment_nos.append(sn)
            elif api_status and api_status != stored_status:
                shipments_repo.update_internal_tracking_summary(
                    sn,
                    row.get("latest_tracking_time") or "",
                    row.get("latest_tracking_desc") or "",
                    status_code=api_status,
                )
                out_log(f"[轨迹同步] {sn} 报文 {status_label} -> {api_status}（无有效轨迹节点）")
                updated += 1
                updated_shipment_nos.append(sn)
            elif is_internal_no_tracking_desc(row.get("latest_tracking_desc")):
                shipments_repo.update_internal_tracking_summary(sn, "", "", log_count=0)
            continue

        if manual_scope:
            written = tracking_repo.replace_for_shipment(sn, logs)
            log_count += written
            latest_time, latest_desc = latest_from_logs(logs)
            shipments_repo.update_internal_tracking_summary(
                sn,
                latest_time,
                latest_desc,
                log_count=written,
                status_code=api_status,
                delivered_time=_delivered_time_for_status(api_status, latest_time),
            )
            updated += 1
            updated_shipment_nos.append(sn)
            if api_status:
                out_log(
                    f"[轨迹同步] {sn} 全量覆盖 {written} 条，报文 {status_label} -> {api_status}，"
                    f"最新 {latest_time}"
                )
            continue

        inserted = tracking_repo.merge_logs_for_shipment(sn, logs)
        log_count += inserted
        latest_time, latest_desc = latest_from_logs(logs)
        stored_time = row.get("latest_tracking_time") or ""
        stored_desc = row.get("latest_tracking_desc") or ""
        summary_same = latest_time == stored_time and latest_desc == stored_desc
        status_same = not api_status or api_status == stored_status
        if inserted == 0 and summary_same and status_same:
            skipped += 1
            continue

        count = tracking_repo.count_by_shipment_no(sn)
        shipments_repo.update_internal_tracking_summary(
            sn,
            latest_time,
            latest_desc,
            log_count=count,
            status_code=api_status,
            delivered_time=_delivered_time_for_status(api_status, latest_time),
        )
        updated += 1
        updated_shipment_nos.append(sn)
        if api_status:
            out_log(
                f"[轨迹同步] {sn} 报文 {status_label} -> {api_status}，"
                f"轨迹 {len(logs)} 条，最新 {latest_time}"
            )
        elif updated % 50 == 0 or idx == total:
            out_log(
                f"[轨迹同步] 进度 {idx}/{total}，"
                f"已更新 {updated} 单，跳过 {skipped} 单，新增轨迹 {log_count} 条"
            )

    unique_errors = list(dict.fromkeys(query_errors))[:20]
    total_batches = (total + batch_size - 1) // batch_size

    out_log(
        f"[轨迹同步] 完成：共 {total} 单，{total_batches} 批；"
        f"更新 {updated} 单，跳过 {skipped} 单（摘要与状态均未变），"
        f"新增轨迹 {log_count} 条；无轨迹 {empty} 单，API 未返回 {not_found} 单"
    )
    if unique_errors:
        out_log(f"[轨迹同步] 接口错误 {len(unique_errors)} 条（详见响应 errors）")

    status = "failed" if unique_errors and updated == 0 else ("partial" if unique_errors else "success")
    if jobs_repo is not None and job_id:
        jobs_repo.finish_job(
            job_id,
            status=status,
            total_shipments=total,
            updated_shipments=updated,
            new_log_count=log_count,
            skipped=skipped,
            empty_count=empty,
            not_found=not_found,
            errors=unique_errors,
        )
    if (
        is_internal_full_batch(shipment_nos)
        and trigger == "scheduled"
        and status in ("success", "partial")
    ):
        record_internal_batch_finished(shipments_repo._database)

    group_alerts = evaluate_groups_after_tracking_sync(
        shipments_repo._database,
        updated_shipment_nos,
        out_log,
    )

    sla_alerts = evaluate_sla_after_tracking_sync(
        shipments_repo._database,
        updated_shipment_nos,
        out_log,
    )

    writeback_nos = (
        [str(row["tracking_number"]).strip() for row in tracking_list if row.get("tracking_number")]
        if manual_scope
        else updated_shipment_nos
    )
    writeback = recalculate_for_shipment_nos(
        shipments_repo._database,
        writeback_nos,
        log=out_log,
    )

    return {
        "jobId": job_id,
        "total": total,
        "updated": updated,
        "skipped": skipped,
        "empty": empty,
        "notFound": not_found,
        "logCount": log_count,
        "excludedNotInTransit": excluded_not_in_transit,
        "errors": unique_errors,
        "batchSize": batch_size,
        "batches": total_batches,
        "logs": log_lines[-200:],
        **group_alerts,
        **sla_alerts,
        "timeWritebackProcessed": writeback.get("processed", 0),
        "timeWritebackApplied": writeback.get("appliedTotal", 0),
        "timeWritebackPendingReview": writeback.get("pendingReviewTotal", 0),
    }


def _empty_result(
    batch_size: int,
    log_lines: list[str] | None = None,
    *,
    excluded_not_in_transit: int = 0,
    job_id: str | None = None,
) -> dict[str, Any]:
    return {
        "jobId": job_id,
        "total": 0,
        "updated": 0,
        "skipped": 0,
        "empty": 0,
        "notFound": 0,
        "logCount": 0,
        "excludedNotInTransit": excluded_not_in_transit,
        "errors": [],
        "batchSize": batch_size,
        "batches": 0,
        "logs": (log_lines or [])[-200:],
    }


def _skipped_internal_batch_result(
    log_lines: list[str],
    reason: str,
) -> dict[str, Any]:
    return {
        "jobId": None,
        "total": 0,
        "updated": 0,
        "skipped": 0,
        "empty": 0,
        "notFound": 0,
        "logCount": 0,
        "errors": [],
        "batchSize": BATCH_SIZE,
        "batches": 0,
        "intervalSkipped": True,
        "skipReason": reason,
        "logs": log_lines[-200:],
    }
