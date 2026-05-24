"""运单追踪号（主单 + 子单）持久化。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .shipment_tracking_numbers_table import TABLE_NAME
from ..last_mile_tracking import normalize_tracking_field_value


def _clean_number(raw: str | None) -> str:
    return normalize_tracking_field_value(raw) or (raw or "").strip()


class ShipmentTrackingNumbersRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_by_shipment_no(self, shipment_no: str) -> list[dict[str, Any]]:
        sn = shipment_no.strip()
        if not sn:
            return []
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE shipment_no = ?
                ORDER BY is_main DESC, tracking_number ASC
                """,
                (sn,),
            ).fetchall()
        return [_row_to_api(r) for r in rows]

    def replace_for_shipment(
        self,
        shipment_no: str,
        main_tracking_number: str | None,
        tracking_numbers: list[str] | None,
    ) -> int:
        """全量替换某运单的追踪号行；返回写入条数。"""
        sn = shipment_no.strip()
        main = _clean_number(main_tracking_number)
        if not sn or not main:
            return 0

        ordered: list[str] = []
        seen: set[str] = set()
        for raw in tracking_numbers or []:
            n = _clean_number(raw)
            if n and n not in seen:
                seen.add(n)
                ordered.append(n)
        if main not in seen:
            ordered.insert(0, main)

        now = now_str()
        with self._database.lock:
            self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE shipment_no = ?",
                (sn,),
            )
            count = 0
            for n in ordered:
                self._conn.execute(
                    f"""
                    INSERT INTO {TABLE_NAME}
                        (id, shipment_no, main_tracking_number, tracking_number,
                         is_main, created_time, updated_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        sn,
                        main,
                        n,
                        1 if n == main else 0,
                        now,
                        now,
                    ),
                )
                count += 1
            self._conn.commit()
        return count


def _row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "shipmentNo": row["shipment_no"],
        "mainTrackingNumber": row["main_tracking_number"],
        "trackingNumber": row["tracking_number"],
        "isMain": bool(row["is_main"]),
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }
