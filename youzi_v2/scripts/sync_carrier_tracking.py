"""定时任务入口：同步全库在途承运商轨迹。用法: python youzi_v2/scripts/sync_carrier_tracking.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from youzi_v2.db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from youzi_v2.db.connection import get_database
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from youzi_v2.services.carrier_tracking_sync import sync_carrier_tracking

CONFIG = ROOT / "config" / "config.json"
DB = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"


def main() -> None:
    db = get_database(DB)
    result = sync_carrier_tracking(
        ShipmentsRepository(db),
        CarrierTrackingLogsRepository(db),
        TrackingSyncJobsRepository(db),
        CONFIG,
        trigger="scheduled",
        log=print,
    )
    print(
        f"完成: 更新 {result['updated']} 单, 新增 {result['logCount']} 条轨迹, "
        f"未匹配/失败 {result['notFound']}"
    )


if __name__ == "__main__":
    main()
