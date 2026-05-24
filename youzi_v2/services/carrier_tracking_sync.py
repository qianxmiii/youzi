"""承运商轨迹同步：仅转运中(IN_TRANSIT)、按 vendor 串行、每批 10 单。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from ..db.shipments_repository import ShipmentsRepository
from ..db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from .carrier_batch_schedule import (
    is_carrier_full_batch,
    record_carrier_batch_finished,
    should_run_scheduled_carrier_batch,
)
from .sync_log import make_sync_logger
from ..carrier_tracking_entry import latest_from_logs
from .carrier_vendors import (
    BATCH_SIZE,
    carrier_vendor_unassigned_reason,
    detect_platform,
    fetch_tracking_batch,
    fetch_tracking_one,
    fetch_txfba_batch_for_rows,
    fetch_wy_batch_for_rows,
    load_vendors_config,
    resolve_vendor_for_row,
)

LogFn = Callable[[str], None]


def sync_carrier_tracking(
    shipments_repo: ShipmentsRepository,
    carrier_repo: CarrierTrackingLogsRepository,
    jobs_repo: TrackingSyncJobsRepository,
    config_path: Path,
    *,
    trigger: str = "manual",
    shipment_nos: list[str] | None = None,
    log: LogFn | None = None,
) -> dict[str, Any]:
    log_lines, out_log = make_sync_logger(log)

    if trigger == "scheduled" and is_carrier_full_batch(shipment_nos):
        ok, skip_reason = should_run_scheduled_carrier_batch(shipments_repo._database)
        if not ok:
            out_log(f"[承运商轨迹] 跳过全库同步：{skip_reason}")
            return _skipped_carrier_batch_result(log_lines, skip_reason or "")

    job_id = jobs_repo.create_job("carrier", trigger)

    try:
        vendors = load_vendors_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        jobs_repo.finish_job(
            job_id,
            status="failed",
            total_shipments=0,
            updated_shipments=0,
            new_log_count=0,
            errors=[str(exc)],
        )
        raise

    vendor_map = {v["name"]: v for v in vendors if v.get("name")}
    requested_nos = (
        len([s for s in shipment_nos if s and s.strip()]) if shipment_nos else 0
    )
    manual_scope = bool(shipment_nos)
    rows = shipments_repo.list_for_carrier_sync(
        shipment_nos,
        include_delivered=manual_scope,
    )
    total = len(rows)
    excluded_not_in_transit = max(0, requested_nos - total) if manual_scope else 0
    if manual_scope:
        out_log(
            f"[承运商轨迹] 指定 {requested_nos} 单，可同步 {total} 单（含已签收）"
            + (
                f"，未匹配 {excluded_not_in_transit} 单"
                if excluded_not_in_transit
                else ""
            )
        )

    by_vendor: dict[str, list[dict[str, str]]] = {}
    unassigned = 0
    errors: list[str] = []
    for row in rows:
        vendor = resolve_vendor_for_row(row, vendor_map)
        if vendor is None:
            unassigned += 1
            sn = row.get("shipment_no") or ""
            reason = carrier_vendor_unassigned_reason(row, vendor_map)
            err_line = f"未匹配承运商/{sn}: {reason}"
            errors.append(err_line)
            out_log(f"[承运商轨迹] {err_line}")
            continue
        name = vendor["name"]
        by_vendor.setdefault(name, []).append({**row, "_vendor": vendor})

    updated = 0
    skipped = 0
    empty = 0
    not_found = 0
    log_count = 0
    vendor_stats: dict[str, dict[str, int]] = {}

    out_log(
        f"[承运商轨迹] 转运中 {total} 单，已匹配 vendor {total - unassigned} 单，未匹配 {unassigned} 单"
    )

    for vendor_name in sorted(by_vendor.keys()):
        group = by_vendor[vendor_name]
        vendor = vendor_map[vendor_name]
        v_stat = {"updated": 0, "newLogs": 0, "batches": 0}
        out_log(f"[承运商轨迹] vendor={vendor_name} 开始，{len(group)} 单")

        for i in range(0, len(group), BATCH_SIZE):
            batch = group[i : i + BATCH_SIZE]
            v_stat["batches"] += 1
            batch_label = f"{i + 1}-{i + len(batch)}/{len(group)}"
            out_log(f"[承运商轨迹] {vendor_name} 第 {v_stat['batches']} 批 ({batch_label})")

            platform = detect_platform(vendor)
            batch_nos = [r["shipment_no"] for r in batch]
            if platform == "txfba":
                tracking_map = fetch_txfba_batch_for_rows(batch, vendor, log=out_log)
            elif platform == "wy":
                tracking_map = fetch_wy_batch_for_rows(batch, vendor, log=out_log)
            elif platform in ("topda", "huawell_cms"):
                tracking_map = fetch_tracking_batch(batch_nos, vendor, log=out_log)
            else:
                tracking_map = {sn: fetch_tracking_one(sn, vendor) for sn in batch_nos}

            for row in batch:
                sn = row["shipment_no"]
                logs, err, carrier_id, outer_tn = tracking_map.get(
                    sn, ([], "未返回", None, None)
                )
                cid = (carrier_id or "").strip()
                if cid and not (row.get("carrier_id") or "").strip():
                    if shipments_repo.set_carrier_id_if_empty(sn, cid):
                        row["carrier_id"] = cid
                tn = (outer_tn or "").strip()
                if tn and not (row.get("tracking_number") or "").strip():
                    if shipments_repo.set_tracking_number_if_empty(sn, tn):
                        row["tracking_number"] = tn
                bill_hint = (row.get("carrier_id") or "").strip()
                if err:
                    err_line = f"{vendor_name}/{sn}: {err}"
                    errors.append(err_line)
                    out_log(f"[承运商轨迹] 失败 {err_line}")
                    not_found += 1
                    continue
                latest_time, latest_desc = latest_from_logs(logs)
                stored_time = row.get("latest_carrier_time") or ""
                stored_desc = row.get("latest_carrier_desc") or ""

                if not logs:
                    empty += 1
                    hint = f" billNo={bill_hint}" if bill_hint else ""
                    out_log(f"[承运商轨迹] {sn} API 无轨迹{hint}")
                else:
                    out_log(
                        f"[承运商轨迹] {sn} 返回 {len(logs)} 条"
                        + (f" billNo={bill_hint}" if bill_hint else "")
                    )

                recon = carrier_repo.reconcile_logs_for_shipment(
                    sn,
                    vendor_name,
                    row.get("carrier_code") or "",
                    logs,
                )
                inserted = int(recon["inserted"])
                deleted = int(recon["deleted"])
                unchanged = bool(recon["unchanged"])
                log_count += inserted
                v_stat["newLogs"] += inserted

                summary_same = latest_time == stored_time and latest_desc == stored_desc
                if unchanged and summary_same:
                    skipped += 1
                    continue

                if deleted:
                    out_log(f"[承运商轨迹] {sn} 对齐：删除本地多余 {deleted} 条")
                if inserted:
                    out_log(f"[承运商轨迹] {sn} 对齐：写入 {inserted} 条")

                count = carrier_repo.count_by_shipment_no(sn)
                shipments_repo.update_carrier_tracking_summary(
                    sn,
                    latest_time,
                    latest_desc,
                    log_count=count,
                    carrier_id=cid or None,
                    tracking_number=tn or None,
                )
                updated += 1
                v_stat["updated"] += 1

        vendor_stats[vendor_name] = v_stat
        out_log(
            f"[承运商轨迹] vendor={vendor_name} 完成，"
            f"更新 {v_stat['updated']} 单，新增 {v_stat['newLogs']} 条"
        )

    status = "failed" if errors and updated == 0 else ("partial" if errors else "success")
    jobs_repo.finish_job(
        job_id,
        status=status,
        total_shipments=total,
        updated_shipments=updated,
        new_log_count=log_count,
        skipped=skipped,
        empty_count=empty,
        not_found=not_found + unassigned,
        errors=errors,
        summary={"vendors": vendor_stats, "unassigned": unassigned},
    )
    if is_carrier_full_batch(shipment_nos) and status in ("success", "partial"):
        record_carrier_batch_finished(shipments_repo._database)

    out_log(
        f"[承运商轨迹] 全部完成：转运中 {total} 单，更新 {updated} 单，"
        f"新增 {log_count} 条，跳过 {skipped}，无轨迹 {empty}，"
        f"失败/未匹配 {not_found + unassigned}"
    )
    for err_line in errors[:20]:
        out_log(f"[承运商轨迹] 错误明细 {err_line}")

    return {
        "jobId": job_id,
        "total": total,
        "updated": updated,
        "skipped": skipped,
        "empty": empty,
        "notFound": not_found + unassigned,
        "logCount": log_count,
        "errors": list(dict.fromkeys(errors))[:20],
        "batchSize": BATCH_SIZE,
        "batches": sum(v["batches"] for v in vendor_stats.values()),
        "unassigned": unassigned,
        "excludedNotInTransit": excluded_not_in_transit,
        "vendorStats": vendor_stats,
        "logs": log_lines[-200:],
    }


def _skipped_carrier_batch_result(
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
        "unassigned": 0,
        "excludedNotInTransit": 0,
        "vendorStats": {},
        "intervalSkipped": True,
        "skipReason": reason,
        "logs": log_lines[-200:],
    }
