"""船期挂靠批量同步（按库内船公司 + 船舶代码）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from ..db.vessel_schedules_repository import VesselSchedulesRepository
from .maritime_schedule import fetch_vessel_schedule, resolve_schedule_provider

LogFn = Callable[[str], None]

_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def _append_schedule_sync_log(line: str) -> None:
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        day = datetime.now().strftime("%Y-%m-%d")
        path = _LOG_DIR / f"vessel-schedule-sync-{day}.log"
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{line}\n")
    except OSError:
        pass


def make_schedule_sync_logger(extra: LogFn | None = None) -> tuple[list[str], LogFn]:
    lines: list[str] = []

    def out_log(msg: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        lines.append(line)
        print(line, flush=True)
        _append_schedule_sync_log(line)
        if extra is not None:
            extra(line)

    return lines, out_log


def sync_one_vessel_schedule(
    repo: VesselSchedulesRepository,
    shipping_company: str,
    vessel_code: str,
    *,
    period: int = 28,
    notes: str | None = None,
) -> dict[str, Any]:
    """从船公司接口拉取单船挂靠并 upsert。"""
    parsed = fetch_vessel_schedule(
        shipping_company,
        vessel_code,
        period=period,
    )
    notes_val = (notes or "").strip() or str(parsed.get("notes") or "")
    detail, created = repo.upsert_from_import(
        vessel_voyage=str(parsed["vesselVoyage"]),
        port_calls=parsed.get("portCalls") or [],
        notes=notes_val,
        vessel_name=parsed.get("vesselName"),
        voyage_no=parsed.get("voyageNo"),
        vessel_code=parsed.get("vesselCode") or vessel_code.strip().upper(),
        shipping_company=parsed.get("shippingCompany"),
        match_by_carrier=True,
    )
    return {
        "voyage": detail,
        "created": created,
        "source": parsed.get("source"),
        "portCount": len(detail.get("portCalls") or []),
    }


def sync_all_vessel_schedules(
    repo: VesselSchedulesRepository,
    *,
    period: int = 28,
    log: LogFn | None = None,
) -> dict[str, Any]:
    """同步库内所有已配置船公司 + 船舶代码的航次挂靠（按承运商去重）。"""
    log_lines, out_log = make_schedule_sync_logger(log)
    targets = repo.list_carrier_sync_targets()
    skipped_incomplete = repo.count_voyages_missing_carrier()

    synced = created = updated = failed = skipped_unsupported = 0
    errors: list[dict[str, str]] = []

    out_log(f"[船期同步] 开始全库同步：{len(targets)} 条承运商目标，周期 {period} 天")
    if skipped_incomplete:
        out_log(f"[船期同步] 跳过 {skipped_incomplete} 条缺少船公司或船舶代码的航次")

    for target in targets:
        company = str(target["shippingCompany"])
        code = str(target["vesselCode"])
        vessel_voyage = str(target.get("vesselVoyage") or "")
        try:
            resolve_schedule_provider(company)
        except ValueError as exc:
            skipped_unsupported += 1
            out_log(f"[船期同步] 跳过 {company}/{code}：{exc}")
            continue

        try:
            result = sync_one_vessel_schedule(repo, company, code, period=period)
            synced += 1
            if result["created"]:
                created += 1
            else:
                updated += 1
            out_log(
                f"[船期同步] 成功 {company}/{code} → "
                f"{result['portCount']} 个挂靠港"
            )
        except ValueError as exc:
            failed += 1
            msg = str(exc)
            errors.append(
                {
                    "shippingCompany": company,
                    "vesselCode": code,
                    "vesselVoyage": vessel_voyage,
                    "message": msg,
                }
            )
            out_log(f"[船期同步] 失败 {company}/{code}：{msg}")

    out_log(
        f"[船期同步] 完成：成功 {synced}，新建 {created}，更新 {updated}，"
        f"失败 {failed}，未接入 {skipped_unsupported}"
    )
    return {
        "total": len(targets),
        "synced": synced,
        "created": created,
        "updated": updated,
        "failed": failed,
        "skipped_unsupported": skipped_unsupported,
        "skipped_incomplete": skipped_incomplete,
        "errors": errors,
        "log": log_lines,
    }
