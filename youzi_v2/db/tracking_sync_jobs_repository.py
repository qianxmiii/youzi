"""轨迹同步任务 tracking_sync_jobs。"""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .tracking_sync_jobs_table import TABLE_NAME


class TrackingSyncJobsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def create_job(self, source: str, trigger_type: str) -> str:
        rid = str(uuid.uuid4())
        now = now_str()
        with self._database.lock:
            self._conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, source, trigger_type, status, started_time
                ) VALUES (?, ?, ?, 'running', ?)
                """,
                (rid, source, trigger_type, now),
            )
            self._conn.commit()
        return rid

    def finish_job(
        self,
        job_id: str,
        *,
        status: str,
        total_shipments: int,
        updated_shipments: int,
        new_log_count: int,
        skipped: int = 0,
        empty_count: int = 0,
        not_found: int = 0,
        errors: list[str] | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        errors = errors or []
        summary = summary or {}
        with self._database.lock:
            self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET status = ?,
                    total_shipments = ?,
                    updated_shipments = ?,
                    new_log_count = ?,
                    skipped = ?,
                    empty_count = ?,
                    not_found = ?,
                    error_count = ?,
                    errors_json = ?,
                    summary_json = ?,
                    finished_time = ?
                WHERE id = ?
                """,
                (
                    status,
                    total_shipments,
                    updated_shipments,
                    new_log_count,
                    skipped,
                    empty_count,
                    not_found,
                    len(errors),
                    json.dumps(errors[:50], ensure_ascii=False),
                    json.dumps(summary, ensure_ascii=False),
                    now_str(),
                    job_id,
                ),
            )
            self._conn.commit()

    def list_jobs(
        self,
        *,
        source: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        where = ""
        params: list[Any] = []
        if source:
            where = "WHERE source = ?"
            params.append(source.strip())

        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {TABLE_NAME} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                {where}
                ORDER BY datetime(started_time) DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            errors_raw = row["errors_json"] or "[]"
            try:
                errors = json.loads(errors_raw)
                if not isinstance(errors, list):
                    errors = []
            except json.JSONDecodeError:
                errors = []
            items.append(
                {
                    "id": row["id"],
                    "source": row["source"],
                    "triggerType": row["trigger_type"],
                    "status": row["status"],
                    "totalShipments": int(row["total_shipments"]),
                    "updatedShipments": int(row["updated_shipments"]),
                    "newLogCount": int(row["new_log_count"]),
                    "skipped": int(row["skipped"]),
                    "emptyCount": int(row["empty_count"]),
                    "notFound": int(row["not_found"]),
                    "errorCount": int(row["error_count"]),
                    "errors": [str(e) for e in errors[:5]],
                    "startedTime": row["started_time"],
                    "finishedTime": row["finished_time"],
                }
            )
        return {"items": items, "total": int(total), "limit": limit, "offset": offset}

    def today_stats(self, source: str) -> dict[str, Any]:
        """当日已完成任务的 updated_shipments / new_log_count 合计。"""
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT
                    COALESCE(SUM(updated_shipments), 0) AS updated_shipments,
                    COALESCE(SUM(new_log_count), 0) AS new_log_count,
                    COUNT(*) AS job_count,
                    MAX(finished_time) AS last_finished
                FROM {TABLE_NAME}
                WHERE source = ?
                  AND status IN ('success', 'partial')
                  AND date(finished_time) = date('now', 'localtime')
                """,
                (source,),
            ).fetchone()
        return {
            "source": source,
            "updatedShipments": int(row["updated_shipments"]),
            "newLogCount": int(row["new_log_count"]),
            "jobCount": int(row["job_count"]),
            "lastFinished": row["last_finished"],
        }
