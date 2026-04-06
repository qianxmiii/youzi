import os
import shutil
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
TOOL_DIR = REPO_ROOT / "tools" / "product_import"
SCRIPT_PATH = TOOL_DIR / "generate_product_import.py"
CONFIG_PATH = TOOL_DIR / "field_mapping.json"
SAMPLES_DIR = TOOL_DIR / "samples"

TEMP_DIR = BASE_DIR / "temp"
UPLOAD_DIR = TEMP_DIR / "uploads"
OUTPUT_DIR = TEMP_DIR / "outputs"

for directory in (UPLOAD_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="youzi_v2 Admin")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


class QuoteRecordIn(BaseModel):
    customer: str = Field(default="", description="客户名")
    channel: str = Field(default="", description="渠道")
    amount: float = Field(default=0, description="报价金额")
    note: str = Field(default="", description="备注")
    extra: dict[str, Any] = Field(default_factory=dict)


class QuoteRecord(QuoteRecordIn):
    id: str
    created_at: str
    updated_at: str


class QuoteStore:
    """框架期内存存储；后续可替换为 DB 层。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: list[QuoteRecord] = [
            QuoteRecord(
                id=str(uuid.uuid4()),
                customer="演示客户A",
                channel="美线卡派",
                amount=12.5,
                note="这是后台框架演示数据",
                extra={},
                created_at=datetime.now().isoformat(timespec="seconds"),
                updated_at=datetime.now().isoformat(timespec="seconds"),
            )
        ]

    def list(self) -> list[QuoteRecord]:
        with self._lock:
            return list(self._items)

    def create(self, data: QuoteRecordIn) -> QuoteRecord:
        now = datetime.now().isoformat(timespec="seconds")
        item = QuoteRecord(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            **data.model_dump(),
        )
        with self._lock:
            self._items.insert(0, item)
        return item

    def update(self, item_id: str, data: QuoteRecordIn) -> QuoteRecord:
        with self._lock:
            for idx, item in enumerate(self._items):
                if item.id == item_id:
                    updated = QuoteRecord(
                        id=item.id,
                        created_at=item.created_at,
                        updated_at=datetime.now().isoformat(timespec="seconds"),
                        **data.model_dump(),
                    )
                    self._items[idx] = updated
                    return updated
        raise KeyError(item_id)

    def delete(self, item_id: str) -> bool:
        with self._lock:
            before = len(self._items)
            self._items = [x for x in self._items if x.id != item_id]
            return len(self._items) != before

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


quote_store = QuoteStore()


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


@app.get("/api/quote-history")
def get_quote_history():
    return quote_store.list()


@app.post("/api/quote-history")
def create_quote_history(payload: QuoteRecordIn):
    return quote_store.create(payload)


@app.put("/api/quote-history/{item_id}")
def update_quote_history(item_id: str, payload: QuoteRecordIn):
    try:
        return quote_store.update(item_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="记录不存在")


@app.delete("/api/quote-history/{item_id}")
def delete_quote_history(item_id: str):
    deleted = quote_store.delete(item_id)
    return {"deleted": deleted}


@app.delete("/api/quote-history")
def clear_quote_history():
    quote_store.clear()
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
