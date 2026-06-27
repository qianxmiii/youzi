"""计划任务页：配置与说明。"""

from __future__ import annotations

from pathlib import Path

from ..db.connection import Database
from .group_archive_settings import (
    GROUP_AUTO_ARCHIVE_INTERVAL_HOURS,
    get_group_archive_settings,
)
from .scheduled_sync_settings import (
    ScheduledSyncSettings,
    get_scheduled_sync_settings,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_scheduled_task_config(database: Database) -> dict:
    sync = get_scheduled_sync_settings(database).to_api_dict()
    archive = get_group_archive_settings(database).to_api_dict()
    out = sync | archive | {
        "scriptPath": str(REPO_ROOT / "youzi_v2" / "scripts" / "sync_all_tracking_scheduled.py"),
        "pollIntervalSec": 60,
    }
    out["schedulerActive"] = bool(
        sync.get("schedulerActive") or archive.get("groupAutoArchiveEnabled")
    )
    return out


def builtin_scheduled_tasks(
    settings: ScheduledSyncSettings,
    database: Database,
) -> list[dict]:
    def interval_label(enabled: bool, hours: float) -> str:
        if not enabled:
            return "已关闭"
        return f"每 {hours:g} 小时"

    archive_settings = get_group_archive_settings(database)
    archive_schedule = (
        "已关闭"
        if not archive_settings.auto_archive_enabled
        else f"每 {GROUP_AUTO_ARCHIVE_INTERVAL_HOURS:g} 小时（约 1 天）"
    )

    return [
        {
            "id": "internal-tracking",
            "name": "内部路由轨迹",
            "source": "internal",
            "schedule": interval_label(
                settings.internal_enabled, settings.internal_interval_hours
            ),
            "description": "从 config.json base_url 拉取内部路由轨迹；可同步转运中/未知/查验，已签收不同步。",
        },
        {
            "id": "carrier-tracking",
            "name": "承运商轨迹",
            "source": "carrier",
            "schedule": interval_label(
                settings.carrier_enabled, settings.carrier_interval_hours
            ),
            "description": "按承运商 vendor 拉取轨迹，仅转运中；全库未满间隔时跳过，避免重启重复拉取。",
        },
        {
            "id": "group-auto-archive",
            "name": "分组自动归档",
            "source": "group-archive",
            "schedule": archive_schedule,
            "description": "将组内全部签收且收款状态为「已付」的分组自动归档；默认关闭，可手动立即执行。",
        },
    ]
