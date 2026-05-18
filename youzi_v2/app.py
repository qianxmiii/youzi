import os
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from .db.addresses_table import AddressesRepository
from .db.connection import get_database
from .db.quote_history_table import QuoteHistoryRepository
from .db.shipments_repository import ShipmentsRepository
from .db.tracking_logs_repository import TrackingLogsRepository
from .schemas.shipments import ShipmentRecordIn, ShipmentUpdateIn
from .schemas.tracking import TrackingSyncRequest, TrackingSyncResult
from .services.shipment_excel import import_excel_file
from .services.tracking_sync import sync_all_tracking

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
TOOL_DIR = REPO_ROOT / "tools" / "product_import"
SCRIPT_PATH = TOOL_DIR / "generate_product_import.py"
CONFIG_PATH = TOOL_DIR / "field_mapping.json"
SAMPLES_DIR = TOOL_DIR / "samples"

TEMP_DIR = BASE_DIR / "temp"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = TEMP_DIR / "uploads"
OUTPUT_DIR = TEMP_DIR / "outputs"

for directory in (UPLOAD_DIR, OUTPUT_DIR, DATA_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="youzi_v2 Admin")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.add_middleware(
    CORSMiddleware,
    # file:// 打开 index.html 时 Origin 为字面量 "null"；仅用 allow_origins=["null"]
    # 在部分环境下预检仍拿不到 ACAO，故用正则一并覆盖本机 http 来源。
    # null=file://；127/localhost=本机；192.168/10=局域网；172.16–31=常见内网
    allow_origin_regex=(
        r"^null$"
        r"|^http://(127\.0\.0\.1|localhost)(:\d+)?$"
        r"|^http://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$"
        r"|^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$"
        r"|^http://172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}(:\d+)?$"
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuoteRecordIn(BaseModel):
    """后台与 index 共用的摘要字段；与 quote_history 表及驼峰 API 对齐。"""

    model_config = ConfigDict(populate_by_name=True)

    customer: str = Field(default="", description="客户代码")
    channel: str = Field(default="", description="渠道/运输方式")
    product_name: str = Field(
        default="00",
        validation_alias=AliasChoices("productName", "product_name"),
        description="品名",
    )
    address: str = Field(default="", description="仓库或地址代码")
    country: str = Field(default="", description="国家")
    amount: float = Field(default=0, description="报价金额 USD")
    note: str = Field(
        default="",
        validation_alias=AliasChoices("note", "notes"),
        description="备注",
    )
    extra: dict[str, Any] = Field(default_factory=dict)


class AddressRecordIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer: str = Field(default="00")
    product_name: str = Field(
        default="00",
        validation_alias=AliasChoices("productName", "product_name"),
    )
    country: str = ""
    address: str = Field(
        default="",
        validation_alias=AliasChoices("address", "address_line"),
        description="地址或仓库代码",
    )
    postal_code: str = Field(
        default="",
        validation_alias=AliasChoices("postalCode", "postcode"),
    )
    company: str = ""
    contact: str = ""
    phone: str = ""
    is_commercial: bool = Field(
        default=True,
        validation_alias=AliasChoices("isCommercial", "is_commercial"),
    )
    is_remote: bool = Field(
        default=False,
        validation_alias=AliasChoices("isRemote", "is_remote"),
    )


_database = get_database(DATA_DIR / "youzi_v2.db")
quote_history_repo = QuoteHistoryRepository(_database)
addresses_repo = AddressesRepository(_database)
shipments_repo = ShipmentsRepository(_database)
tracking_logs_repo = TrackingLogsRepository(_database)
LOGISTICS_CONFIG_PATH = REPO_ROOT / "config" / "config.json"


def resolve_template_xls() -> Path:
    all_xls = sorted(SAMPLES_DIR.glob("*.xls"))
    if not all_xls:
        raise RuntimeError("未找到产品导入模板（.xls）")
    preferred = [p for p in all_xls if "模板" in p.name]
    if preferred:
        return preferred[0]
    candidates = [p for p in all_xls if "自动生成" not in p.name]
    return candidates[0] if candidates else all_xls[0]


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "admin.html", {"request": request})


@app.get("/tools/product-import")
def product_import_page():
    return RedirectResponse(url="/")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "youzi_v2"}


@app.get("/api/v1/health")
def health_v1():
    return {"ok": True, "service": "youzi_v2", "version": "0.2.0"}


# ---------- 运单 shipments ----------


@app.get("/api/v1/shipments")
def list_shipments(
    search: str | None = None,
    status_code: str | None = None,
    country_code: str | None = None,
    channel_code: str | None = None,
    min_stale_days: int | None = None,
    no_tracking: bool | None = None,
    limit: int = 100,
    offset: int = 0,
):
    return shipments_repo.list_rows(
        search=search,
        status_code=status_code,
        country_code=country_code,
        channel_code=channel_code,
        min_stale_days=min_stale_days,
        no_tracking=no_tracking,
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/shipments/{item_id}/tracking-logs")
def list_shipment_tracking_logs(item_id: str, limit: int = 20, offset: int = 0):
    row = shipments_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="运单不存在")
    return tracking_logs_repo.list_by_shipment_no(
        row["shipmentNo"],
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/shipments/{item_id}")
def get_shipment(item_id: str):
    row = shipments_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="运单不存在")
    return row


@app.post("/api/v1/shipments")
def create_shipment(payload: ShipmentRecordIn):
    try:
        return shipments_repo.insert_row(payload.model_dump(by_alias=False))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="运单号已存在") from exc


@app.put("/api/v1/shipments/{item_id}")
def update_shipment(item_id: str, payload: ShipmentUpdateIn):
    try:
        return shipments_repo.update_row(item_id, payload.to_payload())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="运单不存在") from exc


@app.delete("/api/v1/shipments/{item_id}")
def delete_shipment(item_id: str):
    row = shipments_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="运单不存在")
    tracking_logs_repo.delete_by_shipment_no(row["shipmentNo"])
    shipments_repo.delete_row(item_id)
    return {"deleted": True}


@app.post("/api/v1/shipments/sync-tracking", response_model=TrackingSyncResult)
def sync_shipments_tracking(body: TrackingSyncRequest | None = Body(None)):
    """
    从 config/config.json 的 base_url 拉取运单轨迹（与 check_stale_shipments 相同），
    写入 tracking_logs。body.shipmentNos 非空时仅同步指定运单号。
    """
    shipment_nos: list[str] | None = None
    if body and body.shipment_nos:
        shipment_nos = [n.strip() for n in body.shipment_nos if n and n.strip()]
        if not shipment_nos:
            raise HTTPException(status_code=400, detail="运单号列表不能为空")
    try:
        result = sync_all_tracking(
            shipments_repo,
            tracking_logs_repo,
            LOGISTICS_CONFIG_PATH,
            shipment_nos=shipment_nos,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"{exc}。请在仓库根目录 config/config.json 配置 base_url。",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result


@app.post("/api/v1/shipments/import")
async def import_shipments_excel(file: UploadFile = File(...)):
    """
    上传运单 Excel（表头与「运单数据」导出模板一致）。
    按运单号 upsert：已存在则更新，否则新增。
    """
    filename = (file.filename or "").lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 文件")

    task_id = str(uuid.uuid4())
    extension = Path(filename).suffix if Path(filename).suffix else ".xlsx"
    upload_path = UPLOAD_DIR / f"shipment_{task_id}{extension}"

    with upload_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        return import_excel_file(shipments_repo, upload_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if upload_path.exists():
            upload_path.unlink(missing_ok=True)


@app.get("/api/addresses")
def get_addresses():
    """常用地址簿（与 addresses 表字段一一对应；国家/地址/客户/品名为独立列）。"""
    return addresses_repo.list_rows()


@app.post("/api/addresses")
def create_address(payload: AddressRecordIn):
    return addresses_repo.insert_row(
        payload.customer,
        payload.product_name,
        payload.country,
        payload.address,
        payload.postal_code,
        payload.company,
        payload.contact,
        payload.phone,
        payload.is_commercial,
        payload.is_remote,
    )


@app.put("/api/addresses/{item_id}")
def update_address(item_id: str, payload: AddressRecordIn):
    try:
        return addresses_repo.update_row(
            item_id,
            payload.customer,
            payload.product_name,
            payload.country,
            payload.address,
            payload.postal_code,
            payload.company,
            payload.contact,
            payload.phone,
            payload.is_commercial,
            payload.is_remote,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="记录不存在")


@app.delete("/api/addresses/{item_id}")
def delete_address(item_id: str):
    deleted = addresses_repo.delete_row(item_id)
    return {"deleted": deleted}


@app.get("/api/quote-history")
def get_quote_history():
    return quote_history_repo.list_rows()


@app.post("/api/quote-history")
def create_quote_history(payload: QuoteRecordIn):
    return quote_history_repo.insert_admin_simple(
        payload.customer,
        payload.channel,
        payload.amount,
        payload.note,
        product_name=payload.product_name,
        address=payload.address,
        country=payload.country,
    )


@app.post("/api/quote-history/index")
def create_quote_from_index_page(payload: dict[str, Any] = Body(...)):
    """供 index.html 写入完整报价快照（与 logistics.js quoteData 字段一致）。"""
    return quote_history_repo.insert_from_index_payload(payload)


@app.put("/api/quote-history/{item_id}")
def update_quote_history(item_id: str, payload: QuoteRecordIn):
    try:
        return quote_history_repo.update_admin_simple(
            item_id,
            payload.customer,
            payload.channel,
            payload.amount,
            payload.note,
            product_name=payload.product_name,
            address=payload.address,
            country=payload.country,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="记录不存在")


@app.delete("/api/quote-history/{item_id}")
def delete_quote_history(item_id: str):
    deleted = quote_history_repo.delete(item_id)
    return {"deleted": deleted}


@app.delete("/api/quote-history")
def clear_quote_history():
    quote_history_repo.clear()
    return {"ok": True}


@app.post("/api/product-import")
async def product_import(invoice: UploadFile = File(...)):
    filename = (invoice.filename or "").lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 文件")

    task_id = str(uuid.uuid4())
    extension = Path(filename).suffix if Path(filename).suffix else ".xlsx"
    upload_path = UPLOAD_DIR / f"{task_id}{extension}"
    output_path = OUTPUT_DIR / f"{task_id}.xls"

    with upload_path.open("wb") as f:
        shutil.copyfileobj(invoice.file, f)

    try:
        template_path = resolve_template_xls()
        python_bin = os.environ.get("PYTHON", "python")
        cmd = [
            python_bin,
            str(SCRIPT_PATH),
            "--invoice",
            str(upload_path),
            "--template",
            str(template_path),
            "--config",
            str(CONFIG_PATH),
            "--output",
            str(output_path),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "转换失败").strip()
            raise HTTPException(status_code=500, detail=message)
    finally:
        if upload_path.exists():
            upload_path.unlink(missing_ok=True)

    return {"ok": True, "id": task_id, "filename": "产品导入模版.xls"}


@app.get("/api/product-import/download/{task_id}")
def download_file(task_id: str):
    if len(task_id) < 8:
        raise HTTPException(status_code=400, detail="无效 ID")

    output_path = OUTPUT_DIR / f"{task_id}.xls"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.ms-excel",
        filename="产品导入模版.xls",
    )
