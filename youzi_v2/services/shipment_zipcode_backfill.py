"""运单邮编回写：根据地址库（平台仓库 + 第三方地址）补全缺失邮编。"""

from __future__ import annotations

import sqlite3
import threading
from typing import Any, Callable

from ..db.addresses_table import TABLE_NAME as ADDRESSES_TABLE
from ..db.addresses_warehouse_table import TABLE_NAME as WAREHOUSE_TABLE
from ..db.connection import Database
from ..db.shipments_repository import ShipmentsRepository
from .zipcode_backfill_schedule import should_run_scheduled_zipcode_backfill
from .zipcode_backfill_settings import record_zipcode_backfill_finished

LogFn = Callable[[str], None]

_lock = threading.Lock()


def _norm_key(raw: str | None) -> str:
    return (raw or "").strip().upper()


def build_postcode_lookup(database: Database) -> tuple[dict[str, str], dict[str, str]]:
    """平台仓库 code -> 邮编；第三方地址 line/company -> 邮编。"""
    warehouse: dict[str, str] = {}
    private: dict[str, str] = {}
    with database.lock:
        wh_rows = database.conn.execute(
            f"""
            SELECT warehouse_code, postcode FROM {WAREHOUSE_TABLE}
            WHERE TRIM(COALESCE(postcode, '')) != ''
            """
        ).fetchall()
        addr_rows = database.conn.execute(
            f"""
            SELECT address_line, company, postcode FROM {ADDRESSES_TABLE}
            WHERE TRIM(COALESCE(postcode, '')) != ''
            """
        ).fetchall()
    for row in wh_rows:
        code = _norm_key(row["warehouse_code"])
        pc = (row["postcode"] or "").strip()
        if code and pc:
            warehouse[code] = pc
    for row in addr_rows:
        pc = (row["postcode"] or "").strip()
        if not pc:
            continue
        for key in ((row["address_line"] or "").strip(), (row["company"] or "").strip()):
            nk = _norm_key(key)
            if nk:
                private[nk] = pc
    return warehouse, private


def resolve_postcode(
    row: sqlite3.Row,
    warehouse: dict[str, str],
    private: dict[str, str],
) -> str | None:
    keys: list[str] = []
    for field in ("address_code", "delivery_address"):
        nk = _norm_key(row[field] if field in row.keys() else None)
        if nk and nk not in keys:
            keys.append(nk)
    for key in keys:
        if key in warehouse:
            return warehouse[key]
    for key in keys:
        if key in private:
            return private[key]
    return None


def run_zipcode_backfill_batch(
    shipments_repo: ShipmentsRepository,
    *,
    force: bool = False,
    trigger: str = "manual",
    log: LogFn | None = None,
) -> dict[str, Any]:
    database = shipments_repo._database

    def out(msg: str) -> None:
        if log:
            log(msg)

    if not force:
        ok, reason = should_run_scheduled_zipcode_backfill(database)
        if not ok:
            out(f"[邮编回写] 跳过：{reason}")
            return {
                "skipped": True,
                "reason": reason,
                "total": 0,
                "updated": 0,
                "unmatched": 0,
            }

    if not _lock.acquire(blocking=False):
        out("[邮编回写] 跳过：上一轮仍在进行")
        return {
            "skipped": True,
            "reason": "邮编回写进行中",
            "total": 0,
            "updated": 0,
            "unmatched": 0,
        }

    try:
        warehouse, private = build_postcode_lookup(database)
        if not warehouse and not private:
            out("[邮编回写] 地址库无可用邮编数据")
            if trigger == "scheduled" or force:
                record_zipcode_backfill_finished(database)
            return {"skipped": False, "total": 0, "updated": 0, "unmatched": 0}

        candidates = shipments_repo.list_shipments_missing_zipcode()
        total = len(candidates)
        updates: list[tuple[str, str]] = []
        unmatched = 0
        for row in candidates:
            pc = resolve_postcode(row, warehouse, private)
            if pc:
                updates.append((str(row["id"]), pc))
            else:
                unmatched += 1

        updated = shipments_repo.batch_apply_zipcodes(updates)
        out(f"[邮编回写] 更新 {updated}/{total} 单（未匹配 {unmatched}，触发：{trigger}）")
        record_zipcode_backfill_finished(database)
        return {
            "skipped": False,
            "total": total,
            "updated": updated,
            "unmatched": unmatched,
        }
    finally:
        _lock.release()
