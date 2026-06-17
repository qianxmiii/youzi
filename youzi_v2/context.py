import os
import shutil
import sqlite3
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from .db.addresses_table import AddressesRepository
from .db.addresses_warehouse_table import AddressesWarehouseRepository
from .db.code_tables_repository import CodeTablesRepository
from .db.connection import get_database
from .db.dict_repository import DictRepository
from .db.quote_history_table import QuoteHistoryRepository
from .db.shipment_exception_events_repository import ShipmentExceptionEventsRepository
from .db.shipments_repository import ShipmentsRepository
from .db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from .db.tracking_logs_repository import TrackingLogsRepository
from .db.tracking_sync_jobs_repository import TrackingSyncJobsRepository
from .db.customers_repository import CustomersRepository
from .db.channels_repository import ChannelsRepository
from .db.shipment_statistics_repository import ShipmentStatisticsRepository
from .db.port_subscriptions_table import PortSubscriptionsRepository
from .db.shipment_subscriptions_table import ShipmentSubscriptionsRepository
from .db.vessel_schedules_repository import VesselSchedulesRepository
from .schemas.code_tables import CodeTableRecordIn, CodeTableUpdateIn
from .schemas.shipment_exceptions import ShipmentExceptionCloseIn, ShipmentExceptionOpenIn
from .schemas.shipments import (
    ShipmentBatchIdsIn,
    ShipmentBatchResult,
    ShipmentBatchUpdateIn,
    ShipmentRecordIn,
    ShipmentSubscribeBatchResult,
    ShipmentUnsubscribeBatchResult,
    ShipmentUpdateIn,
)
from .schemas.customers import CustomerIn, CustomerSyncResult, CustomerUpdateIn
from .schemas.channels import ChannelIn, ChannelSeedResult, ChannelUpdateIn
from .schemas.vessel_schedules import (
    VesselScheduleFetchIn,
    VesselScheduleSyncAllIn,
    VesselScheduleSyncAllResult,
    VesselVoyageIn,
    VesselVoyageUpdateIn,
    VoyageImportResult,
)
from .services.maritime_schedule import (
    fetch_vessel_schedule,
    list_schedule_providers,
    search_carrier_vessels,
)
from .services.vessel_schedule_sync import (
    sync_all_vessel_schedules,
    sync_one_vessel_schedule,
)
from .schemas.statistics import ShipmentStatisticsOverview
from .schemas.tracking_freshness import TrackingFreshnessStats
from .schemas.scheduled_tasks import (
    ScheduledSyncRunResult,
    ScheduledSyncSettingsUpdate,
    ScheduledTaskConfig,
    ScheduledTaskOverview,
    TrackingSyncJobListResponse,
)
from .schemas.tracking import (
    TrackingSyncDailyStats,
    TrackingSyncRequest,
    TrackingSyncResult,
)
from .services.carrier_tracking_sync import sync_carrier_tracking
from .services.scheduled_tasks_info import (
    build_scheduled_task_config,
    builtin_scheduled_tasks,
)
from .services.scheduled_sync_settings import (
    get_scheduled_sync_settings,
    save_scheduled_sync_settings,
)
from .schemas.world_clocks import WorldClocksSettingsUpdate
from .services.world_clocks_settings import (
    get_world_clocks_settings,
    save_world_clocks_settings,
)
from .services.address_excel import (
    build_export_excel_bytes as build_address_export_bytes,
    build_template_bytes as build_address_template_bytes,
    import_excel_file as import_address_excel,
)
from .services.code_table_excel import build_template_bytes, import_excel_file as import_code_table_excel
from .services.shipment_excel import build_export_excel_bytes, import_excel_file
from .services.maritime_alerts import build_maritime_alerts_overview
from .services.vessel_schedule_excel import (
    build_template_bytes as build_vessel_schedule_template_bytes,
    import_excel_file as import_vessel_schedule_excel,
)
from .services.tracking_sync import sync_all_tracking
from .services.tracking_sync_scheduler import (
    run_scheduled_carrier_sync,
    run_scheduled_internal_sync,
    run_scheduled_tracking_sync,
    start_tracking_sync_scheduler,
)

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
TOOL_DIR = REPO_ROOT / "tools" / "product_import"
SCRIPT_PATH = TOOL_DIR / "generate_product_import.py"
CONFIG_PATH = TOOL_DIR / "field_mapping.json"
SAMPLES_DIR = TOOL_DIR / "samples"

TEMP_DIR = BASE_DIR / "temp"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = TEMP_DIR / "uploads"
OUTPUT_DIR = TEMP_DIR / "outputs"

for directory in (UPLOAD_DIR, OUTPUT_DIR, DATA_DIR):
    directory.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

class QuoteRecordIn(BaseModel):
    """后台与 index 共用的摘要字段；与 quote_history 表及驼峰 API 对齐。"""

    model_config = ConfigDict(populate_by_name=True)

    customer: str = Field(default="", description="客户代码")
    channel: str = Field(default="", description="渠道/运输方式")
    product_name: str = Field(
        default="00",
        validation_alias=AliasChoices("productName", "product_name"),
        description="品名",
    )
    address: str = Field(default="", description="仓库或地址代码")
    country: str = Field(default="", description="国家")
    amount: float = Field(default=0, description="报价金额 USD")
    note: str = Field(
        default="",
        validation_alias=AliasChoices("note", "notes"),
        description="备注",
    )
    extra: dict[str, Any] = Field(default_factory=dict)


class LegacyAddressRecordIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer: str = Field(default="00")
    product_name: str = Field(
        default="00",
        validation_alias=AliasChoices("productName", "product_name"),
    )
    country: str = Field(default="")
    address_line: str = Field(
        default="",
        validation_alias=AliasChoices("address", "address_line"),
    )
    postal_code: str = Field(
        default="",
        validation_alias=AliasChoices("postalCode", "postcode", "postal_code"),
    )
    company: str = Field(default="")
    contact: str = Field(default="")
    phone: str = Field(default="")
    is_commercial: bool = Field(
        default=True,
        validation_alias=AliasChoices("isCommercial", "is_commercial"),
    )
    is_remote: bool = Field(
        default=False,
        validation_alias=AliasChoices("isRemote", "is_remote"),
    )


class WarehouseAddressRecordIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    warehouse_code: str = Field(
        default="",
        validation_alias=AliasChoices("warehouseCode", "warehouse_code"),
        description="仓库代码",
    )
    address_type: str = Field(
        default="",
        validation_alias=AliasChoices("addressType", "address_type"),
        description="AMZ / WFS",
    )
    company: str = Field(default="", description="收件人公司名")
    contact: str = Field(default="", description="收件人")
    country_code: str = Field(
        default="",
        validation_alias=AliasChoices("countryCode", "country_code"),
    )
    postal_code: str = Field(
        default="",
        validation_alias=AliasChoices("postalCode", "postcode", "postal_code"),
    )
    state: str = Field(default="", description="州/省")
    city: str = Field(default="", description="城市")
    address_line1: str = Field(
        default="",
        validation_alias=AliasChoices("addressLine1", "address_line1"),
    )
    address_line2: str = Field(
        default="",
        validation_alias=AliasChoices("addressLine2", "address_line2"),
    )
    address_line3: str = Field(
        default="",
        validation_alias=AliasChoices("addressLine3", "address_line3"),
    )
    phone: str = Field(default="", description="电话")
    note1: str = Field(default="", description="备注一")
    note2: str = Field(default="", description="备注二")


_database = get_database(DATA_DIR / "youzi_v2.db")
quote_history_repo = QuoteHistoryRepository(_database)
addresses_repo = AddressesRepository(_database)
addresses_warehouse_repo = AddressesWarehouseRepository(_database)
shipments_repo = ShipmentsRepository(_database)
shipment_exceptions_repo = ShipmentExceptionEventsRepository(_database)
internal_tracking_repo = TrackingLogsRepository(_database)
carrier_tracking_repo = CarrierTrackingLogsRepository(_database)
tracking_jobs_repo = TrackingSyncJobsRepository(_database)
code_tables_repo = CodeTablesRepository(_database)
dict_repo = DictRepository(_database)
customers_repo = CustomersRepository(_database)
channels_repo = ChannelsRepository(_database)
shipment_statistics_repo = ShipmentStatisticsRepository(_database)
vessel_schedules_repo = VesselSchedulesRepository(_database)
port_subscriptions_repo = PortSubscriptionsRepository(_database)
shipment_subscriptions_repo = ShipmentSubscriptionsRepository(_database)
# 兼容旧名
tracking_logs_repo = internal_tracking_repo
LOGISTICS_CONFIG_PATH = REPO_ROOT / "config" / "config.json"
_tracking_sync_stop: Any = None


def _apply_vip_flags(items: list[dict[str, Any]]) -> None:
    vip_names = customers_repo.vip_customer_name_set()
    for item in items:
        item["isVip"] = (item.get("customer") or "").strip() in vip_names


def resolve_template_xls() -> Path:
    all_xls = sorted(SAMPLES_DIR.glob("*.xls"))
    if not all_xls:
        raise RuntimeError("未找到产品导入模板（.xls）")
    preferred = [p for p in all_xls if "模板" in p.name]
    if preferred:
        return preferred[0]
    candidates = [p for p in all_xls if "自动生成" not in p.name]
    return candidates[0] if candidates else all_xls[0]

__all__ = [name for name in globals() if not name.startswith("__")]
