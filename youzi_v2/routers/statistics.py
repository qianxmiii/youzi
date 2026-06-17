from fastapi import APIRouter

from ..context import *

router = APIRouter()

@router.get("/api/v1/statistics/shipments/overview", response_model=ShipmentStatisticsOverview)
def get_shipment_statistics_overview():
    """运单统计：状态分布、渠道/承运商占比、ATD→ATA 时效基准（预览）。"""
    return ShipmentStatisticsOverview(**shipment_statistics_repo.overview())
