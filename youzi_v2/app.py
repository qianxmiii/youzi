from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .context import (
    BASE_DIR,
    LOGISTICS_CONFIG_PATH,
    carrier_tracking_repo,
    channel_sla_rules_repo,
    internal_tracking_repo,
    shipment_exception_followup_repo,
    shipment_sla_alerts_repo,
    shipments_repo,
    shipment_groups_repo,
    start_tracking_sync_scheduler,
    tracking_jobs_repo,
)
from .routers import (
    addresses,
    channels,
    code_tables,
    customers,
    legacy,
    maritime_alerts,
    pages,
    settings_tasks,
    shipment_groups,
    payment_reminders,
    shipment_sla,
    shipments,
    statistics,
    vessel_schedules,
)

app = FastAPI(title="youzi_v2 Admin")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.add_middleware(
    CORSMiddleware,
    # file:// 打开 index.html 时 Origin 为字面量 "null"；仅用 allow_origins=["null"]
    # 在部分环境下预检仍拿不到 ACAO，故用正则一并覆盖本机 http 来源。
    # null=file://；127/localhost=本机；192.168/10=局域网；172.16–31=常见内网
    allow_origin_regex=(
        r"^null$"
        r"|^http://(127\.0\.0\.1|localhost)(:\d+)?$"
        r"|^http://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$"
        r"|^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$"
        r"|^http://172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}(:\d+)?$"
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_tracking_sync_stop: Any = None


@app.on_event("startup")
def _start_scheduled_tracking_sync() -> None:
    global _tracking_sync_stop
    _tracking_sync_stop = start_tracking_sync_scheduler(
        shipments_repo,
        internal_tracking_repo,
        carrier_tracking_repo,
        tracking_jobs_repo,
        shipment_groups_repo,
        shipment_exception_followup_repo,
        channel_sla_rules_repo,
        shipment_sla_alerts_repo,
        LOGISTICS_CONFIG_PATH,
    )


@app.on_event("shutdown")
def _stop_scheduled_tracking_sync() -> None:
    global _tracking_sync_stop
    if _tracking_sync_stop is not None:
        _tracking_sync_stop.set()


for route_module in (
    pages,
    code_tables,
    payment_reminders,
    shipments,
    statistics,
    customers,
    channels,
    shipment_groups,
    shipment_sla,
    maritime_alerts,
    vessel_schedules,
    settings_tasks,
    addresses,
    legacy,
):
    app.include_router(route_module.router)
