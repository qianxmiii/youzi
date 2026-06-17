from fastapi import APIRouter

from ..context import *

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "admin.html", {"request": request})

@router.get("/tools/product-import")
def product_import_page():
    return RedirectResponse(url="/")

@router.get("/api/health")
def health():
    return {"ok": True, "service": "youzi_v2"}

@router.get("/api/v1/health")
def health_v1():
    return {"ok": True, "service": "youzi_v2", "version": "0.2.0"}

@router.get("/api/v1/dict/{dict_type}")
def list_dict_entries(dict_type: str):
    """按 dict_type 返回字典项（如 country_code → 国家中文名）。"""
    return {"dictType": dict_type.strip(), "items": dict_repo.list_by_type(dict_type)}
