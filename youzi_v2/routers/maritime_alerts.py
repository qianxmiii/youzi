from fastapi import APIRouter

from ..context import *

router = APIRouter()

@router.get("/api/v1/maritime-alerts/overview")
def get_maritime_alerts_overview():
    """首页海运预警：运单海运动态 + 航次挂靠三天内到/离港 + 港口订阅到港通知。"""
    # 直接返回 build 的 camelCase dict；经 response_model 会变成 snake_case，前端无法读取
    return build_maritime_alerts_overview(_database)

@router.post("/api/v1/maritime-alerts/port-arrivals/{notification_id}/read")
def mark_port_arrival_notification_read(notification_id: str):
    if not port_subscriptions_repo.mark_notification_read(notification_id):
        raise HTTPException(status_code=404, detail="通知不存在或已读")
    return {"read": True}

@router.post("/api/v1/maritime-alerts/shipment-arrivals/{notification_id}/read")
def mark_shipment_arrival_notification_read(notification_id: str):
    if not shipment_subscriptions_repo.mark_notification_read(notification_id):
        raise HTTPException(status_code=404, detail="通知不存在或已读")
    return {"read": True}

@router.post("/api/v1/maritime-alerts/notifications/read-all")
def mark_all_maritime_notifications_read():
    """将港口到港、运单轨迹两类未读通知全部标为已读。"""
    port_count = port_subscriptions_repo.mark_all_notifications_read()
    shipment_count = shipment_subscriptions_repo.mark_all_notifications_read()
    return {
        "port": port_count,
        "shipment": shipment_count,
        "total": port_count + shipment_count,
    }
