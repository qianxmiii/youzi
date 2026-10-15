"""企业微信查单前：刷新明细状态、内部/承运商轨迹。"""

from __future__ import annotations

import json
from pathlib import Path

from ..db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from ..db.connection import get_database
from ..db.shipments_repository import ShipmentsRepository
from ..db.tracking_logs_repository import TrackingLogsRepository
from ..db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from .carrier_tracking_sync import sync_carrier_tracking
from .shipment_dps_route_status_sync import sync_route_status_by_waybill_ids
from .tracking_sync import sync_all_tracking
from .wecom_aibot_log import append_wecom_aibot_log

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _REPO_ROOT / "config" / "config.json"
_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"


def read_shipment_query_refresh_enabled(config_path: Path | None = None) -> bool:
    path = config_path or _CONFIG_PATH
    if not path.is_file():
        return True
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    block = data.get("wecom_webhook") if isinstance(data.get("wecom_webhook"), dict) else {}
    raw = block.get("shipment_query_refresh")
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def refresh_shipment_for_wecom_query(
    shipment_no: str,
    *,
    config_path: Path | None = None,
) -> None:
    """按单号拉 DPS 明细状态 + 内部轨迹 + 承运商轨迹；失败写日志不抛错。"""
    sn = (shipment_no or "").strip()
    if not sn:
        return
    cfg = config_path or _CONFIG_PATH
    db = get_database(_DB_PATH)
    shipments_repo = ShipmentsRepository(db)
    internal_repo = TrackingLogsRepository(db)
    carrier_repo = CarrierTrackingLogsRepository(db)
    jobs_repo = TrackingSyncJobsRepository(db)

    try:
        sync_route_status_by_waybill_ids(shipments_repo, cfg, [sn])
    except Exception as exc:
        append_wecom_aibot_log(f"查单刷新明细状态失败 {sn}: {exc}")

    try:
        sync_all_tracking(
            shipments_repo,
            internal_repo,
            cfg,
            shipment_nos=[sn],
            jobs_repo=jobs_repo,
            trigger="manual",
        )
    except Exception as exc:
        append_wecom_aibot_log(f"查单刷新内部轨迹失败 {sn}: {exc}")

    try:
        sync_carrier_tracking(
            shipments_repo,
            carrier_repo,
            jobs_repo,
            cfg,
            trigger="manual",
            shipment_nos=[sn],
        )
    except Exception as exc:
        append_wecom_aibot_log(f"查单刷新承运商轨迹失败 {sn}: {exc}")
