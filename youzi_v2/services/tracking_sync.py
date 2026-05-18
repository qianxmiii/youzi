"""从物流 API 拉取运单轨迹并增量写入 internal_tracking_logs，更新运单内部摘要。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..db.shipments_repository import ShipmentsRepository
from ..db.tracking_logs_repository import TrackingLogsRepository
from ..internal_tracking import is_internal_no_tracking_desc
from .logistics_tracking import (
    BATCH_SIZE,
    _default_log,
    latest_from_logs,
    load_logistics_config,
    logs_from_api_item,
    query_logistics_api,
    shipment_no_from_api_item,
)

LogFn = Callable[[str], None]


def sync_all_tracking(
    shipments_repo: ShipmentsRepository,
    tracking_repo: TrackingLogsRepository,
    config_path: Path,
    *,
    shipment_nos: list[str] | None = None,
    batch_size: int = BATCH_SIZE,
    log: LogFn | None = None,
) -> dict[str, Any]:
    out_log = log or _default_log
    config = load_logistics_config(config_path)
    base_url = config["base_url"]
    batch_size = BATCH_SIZE

    tracking_list = shipments_repo.list_for_tracking_sync(shipment_nos)
    total = len(tracking_list)
    if shipment_nos:
        requested = len([s for s in shipment_nos if s and s.strip()])
        out_log(f"[轨迹同步] 指定 {requested} 单，库内匹配 {total} 单")
    if total == 0:
        out_log("[轨迹同步] 无待同步运单，跳过")
        return _empty_result(batch_size)

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
        logs = logs_from_api_item(item)
        if not logs:
            empty += 1
            if is_internal_no_tracking_desc(row.get("latest_tracking_desc")):
                shipments_repo.update_internal_tracking_summary(sn, "", "", log_count=0)
            continue

        latest_time, latest_desc = latest_from_logs(logs)
        stored_time = row.get("latest_tracking_time") or ""
        stored_desc = row.get("latest_tracking_desc") or ""
        if latest_time == stored_time and latest_desc == stored_desc:
            skipped += 1
            continue

        inserted = tracking_repo.merge_logs_for_shipment(sn, logs)
        log_count += inserted
        count = tracking_repo.count_by_shipment_no(sn)
        shipments_repo.update_internal_tracking_summary(
            sn, latest_time, latest_desc, log_count=count
        )
        updated += 1
        if updated % 50 == 0 or idx == total:
            out_log(
                f"[轨迹同步] 进度 {idx}/{total}，"
                f"已更新 {updated} 单，跳过 {skipped} 单，新增轨迹 {log_count} 条"
            )

    unique_errors = list(dict.fromkeys(query_errors))[:20]
    total_batches = (total + batch_size - 1) // batch_size

    out_log(
        f"[轨迹同步] 完成：共 {total} 单，{total_batches} 批；"
        f"更新 {updated} 单，跳过 {skipped} 单（摘要未变），"
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
        "errors": unique_errors,
        "batchSize": batch_size,
        "batches": total_batches,
    }


def _empty_result(batch_size: int) -> dict[str, Any]:
    return {
        "total": 0,
        "updated": 0,
        "skipped": 0,
        "empty": 0,
        "notFound": 0,
        "logCount": 0,
        "errors": [],
        "batchSize": batch_size,
        "batches": 0,
    }
