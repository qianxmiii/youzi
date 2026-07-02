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
from .zipcode_backfill_settings import (
    ZIPCODE_BACKFILL_INTERVAL_HOURS,
    get_zipcode_backfill_settings,
)
from .shipment_dps_sync_settings import (
    DPS_SYNC_INTERVAL_HOURS,
    get_shipment_dps_sync_settings,
)
from .exception_followup_settings import (
    EXCEPTION_FOLLOWUP_INTERVAL_HOURS,
    get_exception_followup_settings,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_scheduled_task_config(database: Database) -> dict:
    sync = get_scheduled_sync_settings(database).to_api_dict()
    archive = get_group_archive_settings(database).to_api_dict()
    zipcode = get_zipcode_backfill_settings(database).to_api_dict()
    dps_sync = get_shipment_dps_sync_settings(database).to_api_dict()
    exception_followup = get_exception_followup_settings(database).to_api_dict()
    out = sync | archive | zipcode | dps_sync | exception_followup | {
        "scriptPath": str(REPO_ROOT / "youzi_v2" / "scripts" / "sync_all_tracking_scheduled.py"),
        "pollIntervalSec": 60,
    }
    out["schedulerActive"] = bool(
        sync.get("schedulerActive")
        or archive.get("groupAutoArchiveEnabled")
        or zipcode.get("zipcodeBackfillEnabled")
        or dps_sync.get("dpsShipmentSyncEnabled")
        or exception_followup.get("exceptionFollowupEnabled")
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
    zipcode_settings = get_zipcode_backfill_settings(database)
    zipcode_schedule = (
        "已关闭"
        if not zipcode_settings.enabled
        else f"每 {ZIPCODE_BACKFILL_INTERVAL_HOURS:g} 小时（约 1 天）"
    )
    dps_settings = get_shipment_dps_sync_settings(database)
    dps_schedule = (
        "已关闭"
        if not dps_settings.enabled
        else f"每 {DPS_SYNC_INTERVAL_HOURS:g} 小时（约 1 天）"
    )
    eff_start, eff_end = dps_settings.effective_transit_time_range()
    exception_settings = get_exception_followup_settings(database)
    exception_schedule = (
        "已关闭"
        if not exception_settings.enabled
        else f"每 {EXCEPTION_FOLLOWUP_INTERVAL_HOURS:g} 小时（约 1 天）"
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
        {
            "id": "zipcode-backfill",
            "name": "邮编回写",
            "source": "zipcode-backfill",
            "schedule": zipcode_schedule,
            "description": "根据地址库（平台仓库代码、第三方地址）为邮编为空的运单补全 zipcode；默认关闭，可手动立即执行。",
        },
        {
            "id": "exception-followup",
            "name": "异常跟进提醒",
            "source": "exception-followup",
            "schedule": exception_schedule,
            "description": (
                "扫描标记异常的运单：10 天以内每 3 天、10 天以上每 5 天、"
                "20 天以上每 7 天生成顶栏待办跟进提醒；默认关闭，可手动立即执行。"
            ),
        },
        {
            "id": "dps-shipment-sync",
            "name": "DPS 运单同步",
            "source": "dps-shipment-sync",
            "schedule": dps_schedule,
            "description": (
                f"从 config.json shipment_queryByPerson 按发运时间拉取运单并 upsert 至本地；"
                f"默认时间范围当月（当前 {eff_start} ~ {eff_end}）；默认关闭。"
            ),
        },
    ]
