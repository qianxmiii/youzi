"""计划任务页：配置与说明。"""

from __future__ import annotations

from pathlib import Path

from ..db.connection import Database
from .scheduled_sync_settings import (
    ScheduledSyncSettings,
    get_scheduled_sync_settings,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_scheduled_task_config(database: Database) -> dict:
    return get_scheduled_sync_settings(database).to_api_dict() | {
        "scriptPath": str(REPO_ROOT / "youzi_v2" / "scripts" / "sync_all_tracking_scheduled.py"),
        "pollIntervalSec": 60,
    }


def builtin_scheduled_tasks(settings: ScheduledSyncSettings) -> list[dict]:
    def interval_label(enabled: bool, hours: float) -> str:
        if not enabled:
            return "已关闭"
        return f"每 {hours:g} 小时"

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
    ]
