from fastapi import APIRouter, Query

from ..context import *
from ..services.workbench_overview import build_workbench_overview

router = APIRouter()


@router.get("/api/v1/workbench/overview")
def get_workbench_overview(
    todo_limit: int = Query(8, alias="todoLimit", ge=1, le=20),
    arrival_limit: int = Query(6, alias="arrivalLimit", ge=1, le=20),
):
    """工作台首页聚合：今日重点 / 待办 / 近期到港 / 运输概览（模块级容错）。"""
    return build_workbench_overview(
        _database,
        todo_limit=todo_limit,
        arrival_limit=arrival_limit,
    )
