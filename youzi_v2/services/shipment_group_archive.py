"""运单分组归档：手动与自动批处理。"""

from __future__ import annotations

import threading
from typing import Any, Callable

from ..db.connection import Database
from ..db.shipment_groups_repository import ShipmentGroupsRepository
from .group_archive_settings import record_group_auto_archive_finished
from .group_auto_archive_schedule import should_run_scheduled_group_auto_archive

LogFn = Callable[[str], None]

_lock = threading.Lock()


def run_group_auto_archive_batch(
    groups_repo: ShipmentGroupsRepository,
    *,
    force: bool = False,
    trigger: str = "manual",
    log: LogFn | None = None,
) -> dict[str, Any]:
    database = groups_repo._database

    def out(msg: str) -> None:
        if log:
            log(msg)

    if not force:
        ok, reason = should_run_scheduled_group_auto_archive(database)
        if not ok:
            out(f"[分组归档] 跳过：{reason}")
            return {"skipped": True, "reason": reason, "total": 0, "archived": 0, "groupIds": []}

    if not _lock.acquire(blocking=False):
        out("[分组归档] 跳过：上一轮仍在进行")
        return {"skipped": True, "reason": "分组自动归档进行中", "total": 0, "archived": 0, "groupIds": []}

    try:
        candidate_ids = groups_repo.list_auto_archive_candidate_ids()
        total = len(candidate_ids)
        if not total:
            out("[分组归档] 无符合自动归档条件的分组")
            if trigger == "scheduled" or force:
                record_group_auto_archive_finished(database)
            return {"skipped": False, "total": 0, "archived": 0, "groupIds": []}

        archived = groups_repo.auto_archive_candidates(candidate_ids)
        out(f"[分组归档] 自动归档 {archived}/{total} 个分组（触发：{trigger}）")
        record_group_auto_archive_finished(database)
        return {
            "skipped": False,
            "total": total,
            "archived": archived,
            "groupIds": candidate_ids if archived else [],
        }
    finally:
        _lock.release()
