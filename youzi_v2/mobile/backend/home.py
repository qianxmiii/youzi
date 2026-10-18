"""手机首页统计：沿用电脑首页明细状态及今日动态口径，只读取业务库。"""

from datetime import datetime

from fastapi import APIRouter, Request

from ...db.shipment_list_filters import sql_missing_route_status, sql_not_delivered
from ...db.shipment_route_status import ROUTE_STATUS_SEEDS, CUSTOMS_EXCEPTION_ROUTE_STATUSES
from ...db.shipment_exception_followup_repository import ShipmentExceptionFollowupRepository
from .shipments import read_database

router = APIRouter(prefix="/api/mobile/home")

# 与电脑端今日动态一致；节点时间不等于运单 updated_time。
TODAY_ITEMS = (
    ("TODAY_EXCEPTION", "今日异常", "exception_opened_time", "exception"),
    ("TODAY_DEPARTED", "今日离港", "atd", "DEPARTED_POL"),
    ("TODAY_ARRIVED", "今日到港", "ata", "ARRIVED_POD"),
    ("TODAY_INTERNAL_DELIVERED", "今日内签收", "delivered_time", "TRACK_SIGNED"),
    ("TODAY_DEST_TRANSIT", "今日到中转仓", "route_dest_transit_warehouse_time", "DEST_TRANSIT_WAREHOUSE"),
    ("TODAY_LAST_MILE", "今日快递交仓", "route_last_mile_handover_time", "LAST_MILE_HANDOVER"),
    ("TODAY_ROUTE_SIGNED", "今日轨迹签收", "route_track_signed_time", "TRACK_SIGNED"),
)


@router.get("")
def home_summary(request: Request):
    with read_database(request.app.state.settings.database_path) as database:
        unsigned = sql_not_delivered(None)
        unsigned_total = database.conn.execute(f"SELECT COUNT(*) FROM shipments WHERE {unsigned}").fetchone()[0]
        missing = database.conn.execute(f"SELECT COUNT(*) FROM shipments WHERE {unsigned} AND {sql_missing_route_status(None)}").fetchone()[0]
        grouped = database.conn.execute(f"SELECT UPPER(TRIM(COALESCE(route_status, ''))) AS code, COUNT(*) AS count FROM shipments WHERE {unsigned} GROUP BY code").fetchall()
        counts = {row['code']: row['count'] for row in grouped}
        items = [
            {"code": code, "nameZh": label, "count": counts.get(code, 0), "isException": code in CUSTOMS_EXCEPTION_ROUTE_STATUSES, "tone": code}
            for code, _dps, label, _english, _order, milestone in ROUTE_STATUS_SEEDS if milestone
        ]
        items.sort(key=lambda item: not item['isException'])
        items.append({"code": "missing", "nameZh": "无明细状态", "count": missing, "isException": False, "tone": "missing"})
        # 固定字段白名单；同一快照、同一本机日期，避免跨日导致卡片口径不同。
        day = database.conn.execute("SELECT date('now', 'localtime')").fetchone()[0]
        expressions = ', '.join(f"COALESCE(SUM(CASE WHEN date(substr({column}, 1, 10)) = ? THEN 1 ELSE 0 END), 0)" for _code, _label, column, _tone in TODAY_ITEMS)
        today_counts = database.conn.execute(f"SELECT {expressions} FROM shipments", [day] * len(TODAY_ITEMS)).fetchone()
        today = [
            {"code": code, "nameZh": label, "count": today_counts[index], "isException": code == 'TODAY_EXCEPTION', "tone": tone}
            for index, (code, label, _column, tone) in enumerate(TODAY_ITEMS)
        ]
        followups = ShipmentExceptionFollowupRepository(database)
        recent = [
            {key: row.get(key) for key in ('id', 'title', 'message', 'triggeredAt')}
            for row in followups.list_pending_notifications(limit=3)
        ]
        return {"unsignedTotal": unsigned_total, "items": items, "todayItems": today, "today": day, "pendingCount": followups.count_pending(), "recentTodos": recent, "generatedAt": datetime.now().astimezone().isoformat(timespec='seconds')}
