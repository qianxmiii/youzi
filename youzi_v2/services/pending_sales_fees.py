"""待销售确认费用的独立快照与同步。"""
from __future__ import annotations
import json
import threading
from .order_flow_client import fetch_order_flow_rows
from .order_flow_settings import get_order_flow_poll_settings, INTERVAL_SEC
from .order_flow_sync import _elapsed_sec
from ..db.datetime_util import now_str
from ..db.order_flow_repository import normalize_remote_order

CONFIG_KEY = "dps_ddlz_getPendingSalesFeeOrders"
_lock = threading.Lock()

def ensure_schema(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS pending_sales_fee_orders (waybill_no TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS pending_sales_fee_sync (id INTEGER PRIMARY KEY CHECK(id=1), finished TEXT NOT NULL)")

def list_orders(database):
    with database.lock:
        return [json.loads(row[0]) for row in database.conn.execute("SELECT payload FROM pending_sales_fee_orders ORDER BY waybill_no")]

def sync(database, config_path, *, force=False):
    if not force:
        if not get_order_flow_poll_settings(database).enabled:
            return {"skipped": True, "reason": "disabled"}
        with database.lock:
            row = database.conn.execute("SELECT finished FROM pending_sales_fee_sync WHERE id=1").fetchone()
        elapsed = _elapsed_sec(row[0] if row else None)
        if elapsed is not None and elapsed < INTERVAL_SEC:
            return {"skipped": True, "reason": "interval"}
    if not _lock.acquire(blocking=False):
        return {"skipped": True, "reason": "running"}
    try:
        remote = fetch_order_flow_rows(config_path, CONFIG_KEY)
        items = []
        for row in remote:
            item = normalize_remote_order(row)
            if item is None:
                raise ValueError("待确认费用订单格式无效")
            items.append({**item, "ended": False, "statusChanged": False, "statusChangedAt": ""})
        with database.lock:
            conn = database.conn
            try:
                conn.execute("DELETE FROM pending_sales_fee_orders")
                conn.executemany("INSERT INTO pending_sales_fee_orders VALUES (?, ?)", [(x["waybillNo"], json.dumps(x, ensure_ascii=False)) for x in items])
                conn.execute("INSERT OR REPLACE INTO pending_sales_fee_sync VALUES (1, ?)", (now_str(),))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {"skipped": False, "reason": "", "remote": len(items)}
    finally:
        _lock.release()
