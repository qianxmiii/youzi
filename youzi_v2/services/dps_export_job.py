"""DPS 导出异步任务（内存，供前端轮询进度）。"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from ..db.shipments_repository import ShipmentsRepository
from .shipment_dps_cargo_download import build_dps_cargo_data_download
from .shipment_dps_mark_download import build_dps_mark_data_download
from .shipment_dps_mark_split_download import build_dps_mark_split_download
from .shipment_dps_packinglist_download import build_dps_packinglist_download
from .shipment_dps_warehouse_entry_download import (
    build_dps_warehouse_entry_download,
    build_dps_warehouse_entry_pdf_download,
)
from .shipment_dps_warehouseform_download import build_dps_warehouseform_download

ProgressCallback = Callable[[int, str], None]

JobStatus = Literal["queued", "running", "done", "failed"]

_JOB_TTL_SEC = 600


@dataclass
class DpsExportJob:
    id: str
    status: JobStatus = "queued"
    progress: int = 0
    message: str = "排队中…"
    filename: str | None = None
    media_type: str | None = None
    content: bytes | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "filename": self.filename,
            "done": self.status == "done",
            "failed": self.status == "failed",
            "error": self.error,
        }


_jobs: dict[str, DpsExportJob] = {}
_lock = threading.Lock()


def _purge_old_jobs() -> None:
    now = time.time()
    stale = [jid for jid, j in _jobs.items() if now - j.created_at > _JOB_TTL_SEC]
    for jid in stale:
        _jobs.pop(jid, None)


def get_job(job_id: str) -> DpsExportJob | None:
    with _lock:
        _purge_old_jobs()
        return _jobs.get(job_id)


def _run_export_job(
    job: DpsExportJob,
    runner: Callable[[ProgressCallback], tuple[bytes, str, str]],
) -> None:
    def report(p: int, msg: str) -> None:
        with _lock:
            job.progress = max(job.progress, min(100, int(p)))
            job.message = msg

    job.status = "running"
    report(2, "任务已开始…")
    try:
        content, media_type, filename = runner(report)
        with _lock:
            job.content = content
            job.media_type = media_type
            job.filename = filename
            job.status = "done"
            job.progress = 100
            job.message = "已完成"
    except Exception as exc:
        with _lock:
            job.status = "failed"
            job.error = str(exc)
            job.message = str(exc)


def start_dps_export_job(
    runner: Callable[[ProgressCallback], tuple[bytes, str, str]],
) -> str:
    job_id = str(uuid.uuid4())
    job = DpsExportJob(id=job_id)
    with _lock:
        _purge_old_jobs()
        _jobs[job_id] = job
    thread = threading.Thread(
        target=_run_export_job,
        args=(job, runner),
        daemon=True,
        name=f"dps-export-{job_id[:8]}",
    )
    thread.start()
    return job_id


def build_export_runner(
    export_type: str,
    repo: ShipmentsRepository,
    config_path: Path,
    shipment_ids: list[str],
    *,
    split_spec: str | None = None,
) -> Callable[[ProgressCallback], tuple[bytes, str, str]]:
    kind = (export_type or "").strip()
    ids = [x.strip() for x in shipment_ids if x and x.strip()]

    if kind == "markSplit":
        if len(ids) != 1:
            raise ValueError("唛头（拆分）仅支持单票")
        spec = (split_spec or "").strip()
        if not spec:
            raise ValueError("请提供 splitSpec")

        def run_split(cb: ProgressCallback) -> tuple[bytes, str, str]:
            return build_dps_mark_split_download(
                repo,
                config_path,
                ids[0],
                spec,
                progress_cb=cb,
            )

        return run_split

    labels_and_fns: dict[str, tuple[str, Callable[..., tuple[bytes, str, str]]]] = {
        "cargo": ("货箱数据", build_dps_cargo_data_download),
        "mark": ("唛头", build_dps_mark_data_download),
        "packinglist": ("箱单发票", build_dps_packinglist_download),
        "warehouseform": ("排仓单", build_dps_warehouseform_download),
        "warehouseEntry": ("进仓单", build_dps_warehouse_entry_download),
        "warehouseEntryPdf": ("进仓单 PDF", build_dps_warehouse_entry_pdf_download),
    }

    if kind not in labels_and_fns:
        raise ValueError(f"不支持的导出类型：{export_type}")

    label, fn = labels_and_fns[kind]

    def run_generic(cb: ProgressCallback) -> tuple[bytes, str, str]:
        cb(8, f"正在生成{label}…")
        result = fn(repo, config_path, ids)
        cb(95, "即将完成…")
        return result

    return run_generic
