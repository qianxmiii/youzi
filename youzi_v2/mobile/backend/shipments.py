"""手机只读查单：复用既有仓储，独立连接且禁止引导建表或写入业务库。"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import threading
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from ...db.connection import Database
from ...db.shipments_repository import ShipmentsRepository
from ...db.tracking_logs_repository import TrackingLogsRepository
from ...db.carrier_tracking_logs_repository import CarrierTrackingLogsRepository
from ...db.shipment_route_status import route_status_label
from ...db.shipment_order_status import (
    PRE_PORT_STATUSES, TRANSIT_WORKSPACE_STATUSES,
    workspace_status_filter_sql, status_code_filter_sql,
)

router = APIRouter(prefix="/api/mobile/shipments")

STATUS_LABELS = {"0": "已下单", "01": "提货中", "1": "已入仓", "2": "转运中", "3": "已签收", "4": "已取消", "IN_TRANSIT": "转运中", "DELIVERED": "已签收", "INSPECTION": "查验", "UNKNOWN": "未知"}

FIELDS = (
    "id", "shipmentNo", "customer", "customerNo", "customerShipmentId",
    "refShipmentNo", "channelCode", "channelNameZh", "countryCode",
    "addressCode", "zipcode", "ctns", "productName", "carrierCode",
    "carrierNameZh", "trackingNumber", "expressCode", "vesselVoyage",
    "etd", "eta", "atd", "ata", "expectedDeliveryTime", "warehouseEntryTime",
    "deliveredTime", "statusCode", "routeStatus", "latestTrackingTime",
    "latestTrackingDesc", "latestCarrierTime", "latestCarrierDesc", "updatedTime",
)


class ReadOnlyDatabase(Database):
    def __init__(self, path: Path):
        # 不调用 Database.__init__，从而不执行迁移、seed 或启动应用。
        self._path = path.resolve()
        if not self._path.is_file():
            raise FileNotFoundError("业务数据库不存在")
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path.as_uri() + "?mode=ro", uri=True, timeout=3)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA query_only=ON")
        self._conn.execute("BEGIN")


@contextmanager
def read_database(path: Path):
    database = ReadOnlyDatabase(path)
    try:
        yield database
    finally:
        database.conn.close()


def public_shipment(row: dict) -> dict:
    result = {field: row.get(field) for field in FIELDS}
    result["routeStatusLabel"] = route_status_label(row.get("routeStatus"))
    code = str(row.get("statusCode") or "").strip()
    result["statusLabel"] = STATUS_LABELS.get(code, code or "未知")
    result["workspace"] = "preport" if code in PRE_PORT_STATUSES else "transit" if code in TRANSIT_WORKSPACE_STATUSES else None
    if result["workspace"] == "preport":
        result["originWarehouseCode"] = row.get("originWarehouseCode")
        result["chargedWeight"] = row.get("chargedWeight")
    return result


@router.get("")
def list_shipments(request: Request, search: str = Query("", max_length=120), page: int = Query(1, ge=1, le=5000), page_size: int = Query(20, ge=1, le=50), workspace: Literal["preport", "transit"] = "transit", status: Literal["all", "0", "01", "1", "2", "3", "4"] | None = None, customer: str = Query("", max_length=256)):
    with read_database(request.app.state.settings.database_path) as database:
        # 手机统一搜索独立于电脑端“供应商关键词”等筛选语义；仅在固定字段中参数化匹配。
        query = search.strip()
        status = status if status is not None else ("2" if workspace == "transit" else "all")
        if status != "all" and status not in (PRE_PORT_STATUSES if workspace == "preport" else {"2", "3"}):
            raise HTTPException(400, "状态不属于当前运单分类")
        workspace_sql, parameters = workspace_status_filter_sql(workspace, alias="")
        # 选项覆盖当前分类全部运单，不随状态、关键词或分页缩小。
        customers = [row[0] for row in database.conn.execute(
            f"SELECT DISTINCT customer FROM shipments WHERE {workspace_sql} AND TRIM(COALESCE(customer, '')) <> '' ORDER BY customer COLLATE NOCASE",
            parameters,
        ).fetchall()]
        conditions = [workspace_sql]
        if customer.strip():
            conditions.append("customer = ?")
            parameters.append(customer.strip())
        if status != "all":
            status_sql, status_values = status_code_filter_sql(status, alias="")
            conditions.append(status_sql)
            parameters.extend(status_values)
        if query:
            pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            columns = ("shipment_no", "customer_no", "customer_shipment_id", "ref_shipment_no", "customer", "tracking_number")
            conditions.append("(" + " OR ".join(f"{column} LIKE ? ESCAPE '\\'" for column in columns) + ")")
            parameters.extend([pattern] * len(columns))
        where = "WHERE " + " AND ".join(conditions)
        total = database.conn.execute(f"SELECT COUNT(*) FROM shipments {where}", parameters).fetchone()[0]
        rows = database.conn.execute(f"SELECT shipment_no FROM shipments {where} ORDER BY shipment_no DESC LIMIT ? OFFSET ?", [*parameters, page_size, (page - 1) * page_size]).fetchall()
        items = []
        if rows:
            result = ShipmentsRepository(database).list_rows(exact_shipment_nos=[row["shipment_no"] for row in rows], limit=page_size, sort_by="shipmentNo", sort_order="desc")
            items = [public_shipment(row) for row in result["items"]]
        return {"items": items, "total": total, "page": page, "pageSize": page_size, "workspace": workspace, "status": status, "customers": customers}


@router.get("/{shipment_id}")
def shipment_detail(shipment_id: str, request: Request):
    with read_database(request.app.state.settings.database_path) as database:
        row = ShipmentsRepository(database).get_by_id(shipment_id)
        if row is None:
            raise HTTPException(404, "未找到运单，可能已被删除")
        return public_shipment(row)


@router.get("/{shipment_id}/tracking")
def shipment_tracking(shipment_id: str, request: Request, source: Literal["internal", "carrier"] = "internal", page: int = Query(1, ge=1, le=5000), page_size: int = Query(30, ge=1, le=50)):
    with read_database(request.app.state.settings.database_path) as database:
        row = ShipmentsRepository(database).get_by_id(shipment_id)
        if row is None:
            raise HTTPException(404, "未找到运单，可能已被删除")
        repository = TrackingLogsRepository(database) if source == "internal" else CarrierTrackingLogsRepository(database)
        result = repository.list_by_shipment_no(row["shipmentNo"], limit=page_size, offset=(page - 1) * page_size)
        return {"items": [{key: item.get(key) for key in ("id", "trackingTime", "trackingDesc")} for item in result["items"]], "total": result["total"], "page": page, "pageSize": page_size, "source": source}
