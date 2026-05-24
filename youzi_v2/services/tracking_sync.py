"""从物流 API 拉取运单轨迹并增量写入 internal_tracking_logs，更新运单内部摘要。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..db.shipments_repository import ShipmentsRepository
from ..db.tracking_logs_repository import TrackingLogsRepository
from ..internal_tracking import is_internal_no_tracking_desc
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
    if status_code == "DELIVERED" and (latest_time or "").strip():
        return latest_time.strip()
    return None


def sync_all_tracking(
    shipments_repo: ShipmentsRepository,
    tracking_repo: TrackingLogsRepository,
    config_path: Path,
    *,
    shipment_nos: list[str] | None = None,
    batch_size: int = BATCH_SIZE,
    log: LogFn | None = None,
) -> dict[str, Any]:
    log_lines, out_log = make_sync_logger(log)
    config = load_logistics_config(config_path)
    base_url = config["base_url"]
    batch_size = BATCH_SIZE

    requested_nos = (
        len([s for s in shipment_nos if s and s.strip()]) if shipment_nos else 0
    )
    tracking_list = shipments_repo.list_for_tracking_sync(shipment_nos)
    total = len(tracking_list)
    excluded_not_in_transit = max(0, requested_nos - total) if shipment_nos else 0
    if shipment_nos:
        out_log(
            f"[轨迹同步] 指定 {requested_nos} 单，可同步 {total} 单"
            + (
                f"，已跳过已签收等 {excluded_not_in_transit} 单"
                if excluded_not_in_transit
                else ""
            )
        )
    if total == 0:
        out_log("[轨迹同步] 无待同步运单（已签收不参与），跳过")
        return _empty_result(
            batch_size, log_lines, excluded_not_in_transit=excluded_not_in_transit
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

    out_log("[轨迹同步] 开始增量写入…")

    updated = 0
    skipped = 0
    empty = 0
    log_count = 0
    not_found = 0

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
            if api_status and api_status != stored_status:
                shipments_repo.update_internal_tracking_summary(
                    sn,
                    row.get("latest_tracking_time") or "",
                    row.get("latest_tracking_desc") or "",
                    status_code=api_status,
                )
                out_log(f"[轨迹同步] {sn} 报文 {status_label} -> {api_status}（无有效轨迹节点）")
                updated += 1
            elif is_internal_no_tracking_desc(row.get("latest_tracking_desc")):
                shipments_repo.update_internal_tracking_summary(sn, "", "", log_count=0)
            continue

        latest_time, latest_desc = latest_from_logs(logs)
        stored_time = row.get("latest_tracking_time") or ""
        stored_desc = row.get("latest_tracking_desc") or ""
        summary_same = latest_time == stored_time and latest_desc == stored_desc
        status_same = not api_status or api_status == stored_status
        if summary_same and status_same:
            skipped += 1
            continue

        inserted = tracking_repo.merge_logs_for_shipment(sn, logs)
        log_count += inserted
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

    return {
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
    }


def _empty_result(
    batch_size: int,
    log_lines: list[str] | None = None,
    *,
    excluded_not_in_transit: int = 0,
) -> dict[str, Any]:
    return {
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
