"""一次性执行全库轨迹定时同步（内部 + 承运商）。供 Windows 计划任务 / cron 每 2 小时调用。

用法（仓库根目录）:
  python youzi_v2/scripts/sync_all_tracking_scheduled.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from youzi_v2.db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from youzi_v2.db.connection import get_database
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.tracking_logs_repository import TrackingLogsRepository
from youzi_v2.db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from youzi_v2.services.tracking_sync_scheduler import run_scheduled_tracking_sync

CONFIG = ROOT / "config" / "config.json"
DB = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"


def main() -> None:
    db = get_database(DB)
    result = run_scheduled_tracking_sync(
        ShipmentsRepository(db),
        TrackingLogsRepository(db),
        CarrierTrackingLogsRepository(db),
        TrackingSyncJobsRepository(db),
        CONFIG,
        log=print,
    )
    if result.get("skipped"):
        print(f"跳过: {result.get('reason')}")
        return
    internal = result.get("internal") or {}
    carrier = result.get("carrier") or {}
    print(
        "完成 — "
        f"内部: 更新 {internal.get('updated', 0)} 单, 新增轨迹 {internal.get('logCount', 0)} 条; "
        f"承运: 更新 {carrier.get('updated', 0)} 单, 新增轨迹 {carrier.get('logCount', 0)} 条"
    )


if __name__ == "__main__":
    main()
