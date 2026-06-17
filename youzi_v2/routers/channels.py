from fastapi import APIRouter

from ..context import *

router = APIRouter()

@router.get("/api/v1/channels/meta")
def get_channels_meta():
    return {"categories": channels_repo.categories()}

@router.get("/api/v1/channels")
def list_channels(
    search: str | None = None,
    country: str | None = None,
    category: str | None = None,
    active_only: bool | None = Query(None, alias="activeOnly"),
    limit: int = 200,
    offset: int = 0,
):
    return channels_repo.list_rows(
        search=search,
        country=country,
        category=category,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

@router.post("/api/v1/channels/seed-defaults", response_model=ChannelSeedResult)
def seed_default_channels():
    """写入/更新内置渠道列表（按 code 匹配，不删除已有记录）。"""
    return ChannelSeedResult(**channels_repo.seed_defaults())

@router.post("/api/v1/channels", status_code=201)
def create_channel(body: ChannelIn):
    try:
        return channels_repo.create(body.model_dump(by_alias=False))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.patch("/api/v1/channels/{code}")
def update_channel(code: str, body: ChannelUpdateIn):
    data = body.model_dump(exclude_unset=True, by_alias=False)
    if not data:
        row = channels_repo.get_row(code)
        if row is None:
            raise HTTPException(status_code=404, detail="渠道不存在")
        return row
    try:
        return channels_repo.update(code, data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="渠道不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.delete("/api/v1/channels/{code}", status_code=204)
def delete_channel(code: str):
    if not channels_repo.delete(code):
        raise HTTPException(status_code=404, detail="渠道不存在")
    return Response(status_code=204)
