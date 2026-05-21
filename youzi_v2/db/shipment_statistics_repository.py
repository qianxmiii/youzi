"""运单统计分析（聚合查询）。"""

from __future__ import annotations

import statistics
import sqlite3
from datetime import datetime
from typing import Any

from ..internal_tracking import INTERNAL_WAREHOUSE_PLACEHOLDER
from .connection import Database
from .datetime_util import DATETIME_FMT, normalize_tracking_time
from .shipments_table import TABLE_NAME


def _ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def _distribution(rows: list[sqlite3.Row], total: int, key_col: str, label_col: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        key = (r[key_col] or "").strip() or "(空)"
        label = (r[label_col] or "").strip() if label_col else key
        count = int(r["c"])
        out.append(
            {
                "key": key,
                "label": label,
                "count": count,
                "ratio": _ratio(count, total),
            }
        )
    return out


def _parse_date_only(raw: str | None) -> datetime | None:
    text = normalize_tracking_time(raw)
    if not text:
        return None
    for length, fmt in ((19, DATETIME_FMT), (16, "%Y-%m-%d %H:%M"), (10, "%Y-%m-%d")):
        try:
            return datetime.strptime(text[:length], fmt)
        except ValueError:
            continue
    return None


class ShipmentStatisticsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def overview(self) -> dict[str, Any]:
        placeholder = INTERNAL_WAREHOUSE_PLACEHOLDER
        with self._database.lock:
            total = int(
                self._conn.execute(f"SELECT COUNT(*) AS c FROM {TABLE_NAME}").fetchone()["c"]
            )
            status_row = self._conn.execute(
                f"""
                SELECT
                  SUM(CASE WHEN exception_code IS NOT NULL AND TRIM(exception_code) != ''
                      THEN 1 ELSE 0 END) AS exception_cnt,
                  SUM(CASE WHEN (exception_code IS NULL OR TRIM(exception_code) = '')
                      AND (
                        latest_tracking_time IS NULL OR TRIM(latest_tracking_time) = ''
                        OR latest_tracking_desc IS NULL OR TRIM(latest_tracking_desc) = ''
                        OR TRIM(latest_tracking_desc) = ?
                      ) THEN 1 ELSE 0 END) AS no_tracking_cnt,
                  SUM(CASE WHEN (exception_code IS NULL OR TRIM(exception_code) = '')
                      AND NOT (
                        latest_tracking_time IS NULL OR TRIM(latest_tracking_time) = ''
                        OR latest_tracking_desc IS NULL OR TRIM(latest_tracking_desc) = ''
                        OR TRIM(latest_tracking_desc) = ?
                      )
                      AND status_code = 'IN_TRANSIT'
                      THEN 1 ELSE 0 END) AS in_transit_cnt
                FROM {TABLE_NAME}
                """,
                (placeholder, placeholder),
            ).fetchone()
            exc_cnt = int(status_row["exception_cnt"] or 0)
            no_trk_cnt = int(status_row["no_tracking_cnt"] or 0)
            transit_cnt = int(status_row["in_transit_cnt"] or 0)
            other_cnt = max(0, total - exc_cnt - no_trk_cnt - transit_cnt)

            channel_rows = self._conn.execute(
                f"""
                SELECT channel_code AS k, channel_code AS lbl, COUNT(*) AS c
                FROM {TABLE_NAME}
                WHERE channel_code IS NOT NULL AND TRIM(channel_code) != ''
                GROUP BY channel_code
                ORDER BY c DESC
                LIMIT 50
                """
            ).fetchall()
            sea_channel_rows = self._conn.execute(
                f"""
                SELECT channel_code AS k, channel_code AS lbl, COUNT(*) AS c
                FROM {TABLE_NAME}
                WHERE channel_code IS NOT NULL AND TRIM(channel_code) != ''
                  AND (
                    channel_code LIKE '%Sea%'
                    OR channel_code LIKE '%sea%'
                    OR channel_code LIKE '%Truck%'
                    OR channel_code LIKE '%truck%'
                  )
                GROUP BY channel_code
                ORDER BY c DESC
                LIMIT 30
                """
            ).fetchall()
            carrier_rows = self._conn.execute(
                f"""
                SELECT carrier_code AS k, carrier_code AS lbl, COUNT(*) AS c
                FROM {TABLE_NAME}
                WHERE carrier_code IS NOT NULL AND TRIM(carrier_code) != ''
                GROUP BY carrier_code
                ORDER BY c DESC
                LIMIT 50
                """
            ).fetchall()
            atd_ata_rows = self._conn.execute(
                f"""
                SELECT atd, ata FROM {TABLE_NAME}
                WHERE atd IS NOT NULL AND TRIM(atd) != ''
                  AND ata IS NOT NULL AND TRIM(ata) != ''
                """
            ).fetchall()

        status_distribution = [
            {
                "key": "EXCEPTION",
                "label": "异常",
                "count": exc_cnt,
                "ratio": _ratio(exc_cnt, total),
            },
            {
                "key": "NO_TRACKING",
                "label": "无轨迹",
                "count": no_trk_cnt,
                "ratio": _ratio(no_trk_cnt, total),
            },
            {
                "key": "IN_TRANSIT",
                "label": "转运中",
                "count": transit_cnt,
                "ratio": _ratio(transit_cnt, total),
            },
            {
                "key": "OTHER",
                "label": "其它",
                "count": other_cnt,
                "ratio": _ratio(other_cnt, total),
            },
        ]

        deltas: list[float] = []
        for r in atd_ata_rows:
            atd_dt = _parse_date_only(r["atd"])
            ata_dt = _parse_date_only(r["ata"])
            if not atd_dt or not ata_dt:
                continue
            days = (ata_dt.date() - atd_dt.date()).days
            if days >= 0:
                deltas.append(float(days))

        baseline: dict[str, Any] = {
            "available": len(deltas) > 0,
            "sampleCount": len(deltas),
            "avgDays": None,
            "stdDevDays": None,
            "minDays": None,
            "maxDays": None,
            "description": "开船(ATD) → 到港(ATA) 自然日",
        }
        if deltas:
            baseline["avgDays"] = round(sum(deltas) / len(deltas), 2)
            baseline["minDays"] = int(min(deltas))
            baseline["maxDays"] = int(max(deltas))
            baseline["stdDevDays"] = round(
                statistics.stdev(deltas) if len(deltas) >= 2 else 0.0, 2
            )

        sea_total = sum(int(r["c"]) for r in sea_channel_rows)

        return {
            "total": total,
            "statusDistribution": status_distribution,
            "channelDistribution": _distribution(channel_rows, total, "k", "lbl"),
            "seaChannelDistribution": _distribution(
                sea_channel_rows, sea_total or total, "k", "lbl"
            ),
            "seaChannelTotal": sea_total,
            "carrierDistribution": _distribution(carrier_rows, total, "k", "lbl"),
            "transitBaseline": baseline,
        }
