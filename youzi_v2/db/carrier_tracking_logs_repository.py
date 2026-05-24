"""承运商轨迹 carrier_tracking_logs CRUD。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..carrier_tracking_entry import (
    CarrierTrackingLogEntry,
    carrier_logs_unchanged,
    coerce_carrier_logs,
)
from .carrier_tracking_logs_table import TABLE_NAME
from .connection import Database
from .datetime_util import now_str


def _row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    keys = row.keys()
    vendor_event_id = (
        (row["vendor_event_id"] or "").strip()
        if "vendor_event_id" in keys
        else ""
    )
    return {
        "id": row["id"],
        "shipmentNo": row["shipment_no"],
        "vendorName": row["vendor_name"],
        "carrierCode": row["carrier_code"],
        "trackingTime": row["tracking_time"],
        "trackingDesc": row["tracking_desc"],
        "vendorEventId": vendor_event_id or None,
        "createdTime": row["created_time"],
    }


def _entry_from_row(row: sqlite3.Row) -> CarrierTrackingLogEntry:
    keys = row.keys()
    eid = (
        (row["vendor_event_id"] or "").strip()
        if "vendor_event_id" in keys
        else None
    ) or None
    return CarrierTrackingLogEntry.from_row(
        str(row["tracking_time"]),
        str(row["tracking_desc"] or ""),
        eid,
    )


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
                ORDER BY datetime(tracking_time) DESC, id DESC
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

    def _list_entries_for_vendor(
        self, shipment_no: str, vendor_name: str
    ) -> list[CarrierTrackingLogEntry]:
        sn = shipment_no.strip()
        vn = vendor_name or ""
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE shipment_no = ? AND vendor_name = ?
                """,
                (sn, vn),
            ).fetchall()
        return [_entry_from_row(r) for r in rows]

    def reconcile_logs_for_shipment(
        self,
        shipment_no: str,
        vendor_name: str,
        carrier_code: str,
        logs: list[CarrierTrackingLogEntry] | list[tuple[str, str]] | list,
    ) -> dict[str, int | bool]:
        """
        以 API 轨迹为准对齐本 vendor（含 vendor_event_id 比对）。
        返回 inserted / deleted / unchanged。
        """
        sn = shipment_no.strip()
        vn = vendor_name or ""
        cc = carrier_code or ""
        api_logs = coerce_carrier_logs(logs)

        with self._database.lock:
            existing_rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE shipment_no = ? AND vendor_name = ?
                """,
                (sn, vn),
            ).fetchall()
            existing = [_entry_from_row(r) for r in existing_rows]
            if carrier_logs_unchanged(existing, api_logs):
                return {"inserted": 0, "deleted": 0, "unchanged": True}

            cur = self._conn.execute(
                f"""
                DELETE FROM {TABLE_NAME}
                WHERE shipment_no = ? AND vendor_name = ?
                """,
                (sn, vn),
            )
            deleted = int(cur.rowcount)
            now = now_str()
            for entry in api_logs:
                self._conn.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (
                        id, shipment_no, vendor_name, carrier_code,
                        tracking_time, tracking_desc, vendor_event_id, created_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        sn,
                        vn,
                        cc,
                        entry.tracking_time,
                        entry.tracking_desc,
                        entry.vendor_event_id,
                        now,
                    ),
                )
            self._conn.commit()
        return {
            "inserted": len(api_logs),
            "deleted": deleted,
            "unchanged": False,
        }

    def merge_logs_for_shipment(
        self,
        shipment_no: str,
        vendor_name: str,
        carrier_code: str,
        logs: list,
    ) -> int:
        """保留兼容；新同步请用 reconcile_logs_for_shipment。"""
        result = self.reconcile_logs_for_shipment(
            shipment_no, vendor_name, carrier_code, logs
        )
        if result["unchanged"]:
            return 0
        return int(result["inserted"])

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
