"""手机异常跟进：读取既有通知，只更新通知自身的已读及完成状态。"""

from pathlib import Path
import sqlite3
import threading
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from ...db.connection import Database
from ...db.shipment_exception_followup_repository import (
    ShipmentExceptionFollowupRepository, _notification_to_api,
)
from ...db.shipment_order_status import PRE_PORT_STATUSES, TRANSIT_WORKSPACE_STATUSES
from .shipments import read_database

router = APIRouter(prefix="/api/mobile/todos")
TABLE = "shipment_exception_followup_notifications"


class NotificationDatabase(Database):
    def __init__(self, path: Path):
        # 仅打开已有库，不执行 Database 的建表、seed、迁移或后台任务。
        self._path = path.resolve()
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path.as_uri() + "?mode=rw", uri=True, timeout=3)
        self._conn.row_factory = sqlite3.Row


@router.get("")
def list_todos(request: Request, scope: Literal["pending", "resolved", "all"] = "pending", search: str = Query("", max_length=120), page: int = Query(1, ge=1, le=5000), page_size: int = Query(20, ge=1, le=50)):
    with read_database(request.app.state.settings.database_path) as database:
        conditions, parameters = [], []
        if scope != "all":
            conditions.append("TRIM(COALESCE(n.resolved_at, '')) " + ("= ''" if scope == "pending" else "<> ''"))
        if search.strip():
            pattern = "%" + search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            conditions.append("(n.shipment_no LIKE ? ESCAPE '\\' OR s.customer LIKE ? ESCAPE '\\')")
            parameters.extend([pattern, pattern])
        join = f"FROM {TABLE} n LEFT JOIN shipments s ON s.id = n.shipment_id LEFT JOIN shipment_exception_codes ec ON ec.code = n.exception_code"
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        total = database.conn.execute(f"SELECT COUNT(*) {join} {where}", parameters).fetchone()[0]
        pending = database.conn.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE TRIM(COALESCE(resolved_at, '')) = ''").fetchone()[0]
        rows = database.conn.execute(
            f"SELECT n.*, s.customer, s.status_code, s.id AS existing_shipment_id, COALESCE(ec.name_zh, n.exception_code) AS exception_name_zh {join} {where} ORDER BY datetime(n.triggered_at) DESC, n.id DESC LIMIT ? OFFSET ?",
            [*parameters, page_size, (page - 1) * page_size],
        ).fetchall()
        items = []
        for row in rows:
            item = _notification_to_api(row)
            # 内部事件键、提醒周期不属于手机展示字段。
            item.pop("eventKey", None)
            item.pop("followupIntervalDays", None)
            code = str(row["status_code"] or "").strip()
            item["workspace"] = "preport" if code in PRE_PORT_STATUSES else "transit" if code in TRANSIT_WORKSPACE_STATUSES else None
            item["shipmentAvailable"] = row["existing_shipment_id"] is not None
            items.append(item)
        return {"items": items, "total": total, "pendingCount": pending, "page": page, "pageSize": page_size}


@router.post("/{notification_id}/{action}")
def update_todo(notification_id: str, action: Literal["read", "resolve"], request: Request):
    database = NotificationDatabase(request.app.state.settings.database_path)
    try:
        exists = database.conn.execute(f"SELECT 1 FROM {TABLE} WHERE id = ?", (notification_id,)).fetchone()
        if exists is None:
            raise HTTPException(404, "待办不存在，请刷新列表")
        repository = ShipmentExceptionFollowupRepository(database)
        updated = repository.mark_read(notification_id) if action == "read" else repository.mark_resolved(notification_id)
        return {"ok": True, "updated": updated}
    finally:
        database.conn.close()
