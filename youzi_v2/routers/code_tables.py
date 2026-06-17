from fastapi import APIRouter

from ..context import *

router = APIRouter()

@router.get("/api/v1/admin/code-tables")
def list_code_table_types():
    from ..db.code_tables_repository import list_table_meta as _list_table_meta

    return {"tables": _list_table_meta()}

@router.get("/api/v1/admin/code-tables/{table_name}")
def list_code_table_rows(
    table_name: str,
    search: str | None = None,
    limit: int = 200,
    offset: int = 0,
):
    try:
        return code_tables_repo.list_rows(
            table_name, search=search, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/api/v1/admin/code-tables/{table_name}/template")
def download_code_table_template(table_name: str):
    try:
        data = build_template_bytes(table_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{table_name}_template.xlsx"'
        },
    )

@router.get("/api/v1/admin/code-tables/{table_name}/{code}")
def get_code_table_row(table_name: str, code: str):
    try:
        row = code_tables_repo.get_row(table_name, code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return row

@router.post("/api/v1/admin/code-tables/{table_name}")
def create_code_table_row(table_name: str, payload: CodeTableRecordIn):
    try:
        return code_tables_repo.insert_row(table_name, payload.to_payload())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="编码已存在") from exc

@router.put("/api/v1/admin/code-tables/{table_name}/{code}")
def update_code_table_row(table_name: str, code: str, payload: CodeTableUpdateIn):
    try:
        return code_tables_repo.update_row(table_name, code, payload.to_payload())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="记录不存在") from exc

@router.delete("/api/v1/admin/code-tables/{table_name}/{code}")
def delete_code_table_row(table_name: str, code: str):
    try:
        deleted = code_tables_repo.delete_row(table_name, code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"deleted": True}

@router.post("/api/v1/admin/code-tables/{table_name}/import")
async def import_code_table_excel(table_name: str, file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 文件")
    task_id = str(uuid.uuid4())
    extension = Path(filename).suffix if Path(filename).suffix else ".xlsx"
    upload_path = UPLOAD_DIR / f"code_table_{task_id}{extension}"
    with upload_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        return import_code_table_excel(code_tables_repo, table_name, upload_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if upload_path.exists():
            upload_path.unlink(missing_ok=True)
