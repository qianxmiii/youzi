"""承运商轨迹 carrier_tracking_logs CRUD。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .carrier_tracking_logs_table import TABLE_NAME
from .connection import Database
from .datetime_util import now_str


def _row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "shipmentNo": row["shipment_no"],
        "vendorName": row["vendor_name"],
        "carrierCode": row["carrier_code"],
        "trackingTime": row["tracking_time"],
        "trackingDesc": row["tracking_desc"],
        "createdTime": row["created_time"],
    }


class CarrierTrackingLogsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_by_shipment_no(
        self,
        shipment_no: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        sn = shipment_no.strip()
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {TABLE_NAME} WHERE shipment_no = ?",
                (sn,),
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE shipment_no = ?
                ORDER BY datetime(tracking_time) DESC, datetime(created_time) DESC
                LIMIT ? OFFSET ?
                """,
                (sn, limit, offset),
            ).fetchall()
        return {
            "items": [_row_to_api(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def merge_logs_for_shipment(
        self,
        shipment_no: str,
        vendor_name: str,
        carrier_code: str,
        logs: list[tuple[str, str]],
    ) -> int:
        sn = shipment_no.strip()
        if not logs:
            return 0
        now = now_str()
        inserted = 0
        with self._database.lock:
            for tracking_time, tracking_desc in logs:
                cur = self._conn.execute(
                    f"""
                    INSERT OR IGNORE INTO {TABLE_NAME} (
                        id, shipment_no, vendor_name, carrier_code,
                        tracking_time, tracking_desc, created_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        sn,
                        vendor_name or "",
                        carrier_code or "",
                        tracking_time,
                        tracking_desc or "",
                        now,
                    ),
                )
                inserted += cur.rowcount
            self._conn.commit()
        return inserted

    def count_by_shipment_no(self, shipment_no: str) -> int:
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {TABLE_NAME} WHERE shipment_no = ?",
                (shipment_no.strip(),),
            ).fetchone()
        return int(row["c"])

    def delete_by_shipment_no(self, shipment_no: str) -> int:
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE shipment_no = ?",
                (shipment_no.strip(),),
            )
            self._conn.commit()
            return cur.rowcount
