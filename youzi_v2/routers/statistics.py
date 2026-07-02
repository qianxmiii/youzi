from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from ..context import *

router = APIRouter()


def _performance_query(
    date_from: str | None = Query(None, alias="dateFrom"),
    date_to: str | None = Query(None, alias="dateTo"),
    date_basis: str = Query("atd", alias="dateBasis"),
    channel_code: str | None = Query(None, alias="channelCode"),
    carrier_code: str | None = Query(None, alias="carrierCode"),
    customer: str | None = None,
    destination_port_code: str | None = Query(None, alias="destinationPortCode"),
) -> ShipmentPerformanceQuery:
    return ShipmentPerformanceQuery(
        date_from=date_from,
        date_to=date_to,
        date_basis=date_basis,
        channel_code=channel_code,
        carrier_code=carrier_code,
        customer=customer,
        destination_port_code=destination_port_code,
    )


@router.get("/api/v1/statistics/shipments/overview", response_model=ShipmentStatisticsOverview)
def get_shipment_statistics_overview():
    """运单统计：状态分布、渠道/承运商占比、ATD→ATA 时效基准（预览）。"""
    return ShipmentStatisticsOverview(**shipment_statistics_repo.overview())


@router.get(
    "/api/v1/statistics/shipment-performance",
    response_model=ShipmentPerformanceAnalysis,
)
def get_shipment_performance_analysis(
    query: ShipmentPerformanceQuery = Depends(_performance_query),
):
    """运输时效分析：总览与渠道/承运商/客户聚合。"""
    return ShipmentPerformanceAnalysis(**performance_statistics_repo.analyze(query))


@router.get(
    "/api/v1/statistics/shipment-performance/details",
    response_model=ShipmentPerformanceDetailsResponse,
)
def get_shipment_performance_details(
    query: ShipmentPerformanceQuery = Depends(_performance_query),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    sort_by: str = Query("fullTransitDays", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
):
    return ShipmentPerformanceDetailsResponse(
        **performance_statistics_repo.details(
            query,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )


@router.get("/api/v1/statistics/shipment-performance/export")
def export_shipment_performance(
    query: ShipmentPerformanceQuery = Depends(_performance_query),
):
    csv_text, truncated = performance_statistics_repo.export_csv(query)
    headers = {"Content-Disposition": 'attachment; filename="shipment-performance.csv"'}
    if truncated:
        headers["X-Performance-Truncated"] = "1"
    return Response(
        content="\ufeff" + csv_text,
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
