"""运单轨迹订阅与更新通知。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Literal

from .connection import Database
from .datetime_util import now_str
from .shipments_table import TABLE_NAME as SHIPMENTS_TABLE

TrackingSource = Literal["internal", "carrier"]

SUBSCRIPTIONS_TABLE = "shipment_subscriptions"
NOTIFICATIONS_TABLE = "shipment_arrival_notifications"

_CREATE_SUBSCRIPTIONS_SQL = f"""
CREATE TABLE IF NOT EXISTS {SUBSCRIPTIONS_TABLE} (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL UNIQUE,
    shipment_no TEXT NOT NULL DEFAULT '',
    vessel_voyage TEXT NOT NULL DEFAULT '',
    destination_port_code TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    last_notified_ata TEXT NOT NULL DEFAULT '',
    last_notified_internal_time TEXT NOT NULL DEFAULT '',
    last_notified_carrier_time TEXT NOT NULL DEFAULT ''
)
"""

_CREATE_NOTIFICATIONS_SQL = f"""
CREATE TABLE IF NOT EXISTS {NOTIFICATIONS_TABLE} (
    id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL,
    shipment_id TEXT NOT NULL,
    shipment_no TEXT NOT NULL DEFAULT '',
    vessel_voyage TEXT NOT NULL DEFAULT '',
    destination_port_code TEXT NOT NULL DEFAULT '',
    ata TEXT NOT NULL DEFAULT '',
    tracking_source TEXT NOT NULL DEFAULT '',
    latest_time TEXT NOT NULL DEFAULT '',
    latest_desc TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    read_at TEXT NOT NULL DEFAULT ''
)
"""


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r[1]) for r in rows}


def _add_column_if_missing(
    conn: sqlite3.Connection, table: str, name: str, ddl: str
) -> None:
    if name not in _table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SUBSCRIPTIONS_SQL)
    conn.execute(_CREATE_NOTIFICATIONS_SQL)
    _add_column_if_missing(
        conn, SUBSCRIPTIONS_TABLE, "last_notified_internal_time", "TEXT NOT NULL DEFAULT ''"
    )
    _add_column_if_missing(
        conn, SUBSCRIPTIONS_TABLE, "last_notified_carrier_time", "TEXT NOT NULL DEFAULT ''"
    )
    _add_column_if_missing(
        conn, NOTIFICATIONS_TABLE, "tracking_source", "TEXT NOT NULL DEFAULT ''"
    )
    _add_column_if_missing(conn, NOTIFICATIONS_TABLE, "latest_time", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, NOTIFICATIONS_TABLE, "latest_desc", "TEXT NOT NULL DEFAULT ''")
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{SUBSCRIPTIONS_TABLE}_shipment_no
        ON {SUBSCRIPTIONS_TABLE}(shipment_no)
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{NOTIFICATIONS_TABLE}_unread
        ON {NOTIFICATIONS_TABLE}(read_at, created_at)
        """
    )


def _notification_to_api(row: sqlite3.Row) -> dict[str, Any]:
    source = (row["tracking_source"] or "").strip() if "tracking_source" in row.keys() else ""
    latest_time = (row["latest_time"] or "").strip() if "latest_time" in row.keys() else ""
    latest_desc = (row["latest_desc"] or "").strip() if "latest_desc" in row.keys() else ""
    if not source and (row["ata"] or "").strip():
        source = "arrival"
        latest_time = (row["ata"] or "").strip()
        latest_desc = "实际到港"
    customer = ""
    if "shipment_customer" in row.keys():
        customer = (row["shipment_customer"] or "").strip()
    return {
        "id": row["id"],
        "subscriptionId": row["subscription_id"],
        "shipmentId": row["shipment_id"],
        "shipmentNo": row["shipment_no"],
        "customer": customer,
        "vesselVoyage": row["vessel_voyage"],
        "destinationPortCode": row["destination_port_code"],
        "trackingSource": source,
        "latestTime": latest_time,
        "latestDesc": latest_desc,
        "createdAt": row["created_at"],
        "readAt": row["read_at"] or None,
    }


class ShipmentSubscriptionsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def subscribed_shipment_ids(self) -> set[str]:
        with self._database.lock:
            rows = self._conn.execute(
                f"SELECT shipment_id FROM {SUBSCRIPTIONS_TABLE}"
            ).fetchall()
        return {str(r["shipment_id"]) for r in rows}

    def _baseline_tracking_times(self, row: sqlite3.Row) -> tuple[str, str]:
        internal = ""
        carrier = ""
        if "latest_tracking_time" in row.keys():
            internal = (row["latest_tracking_time"] or "").strip()
        if "latest_carrier_time" in row.keys():
            carrier = (row["latest_carrier_time"] or "").strip()
        return internal, carrier

    def subscribe(self, shipment_id: str) -> dict[str, Any]:
        sid = shipment_id.strip()
        if not sid:
            raise ValueError("运单 id 无效")
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {SHIPMENTS_TABLE} WHERE id = ?",
                (sid,),
            ).fetchone()
            if row is None:
                raise KeyError(sid)

            internal_t, carrier_t = self._baseline_tracking_times(row)
            existing = self._conn.execute(
                f"SELECT id FROM {SUBSCRIPTIONS_TABLE} WHERE shipment_id = ?",
                (sid,),
            ).fetchone()
            if existing:
                sub_id = existing["id"]
                self._conn.execute(
                    f"""
                    UPDATE {SUBSCRIPTIONS_TABLE}
                    SET last_notified_internal_time = ?,
                        last_notified_carrier_time = ?
                    WHERE id = ?
                    """,
                    (internal_t, carrier_t, sub_id),
                )
            else:
                sub_id = str(uuid.uuid4())
                now = now_str()
                self._conn.execute(
                    f"""
                    INSERT INTO {SUBSCRIPTIONS_TABLE} (
                        id, shipment_id, shipment_no, vessel_voyage,
                        destination_port_code, created_at,
                        last_notified_internal_time, last_notified_carrier_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sub_id,
                        sid,
                        row["shipment_no"],
                        row["vessel_voyage"] or "",
                        row["destination_port_code"] or "",
                        now,
                        internal_t,
                        carrier_t,
                    ),
                )
            self._conn.commit()
        return {"subscribed": True, "shipmentId": sid}

    def subscribe_many(self, shipment_ids: list[str]) -> dict[str, Any]:
        subscribed = 0
        errors: list[dict[str, str]] = []
        for raw_id in shipment_ids:
            sid = (raw_id or "").strip()
            if not sid:
                continue
            try:
                self.subscribe(sid)
                subscribed += 1
            except KeyError:
                errors.append({"shipmentId": sid, "message": "运单不存在"})
            except ValueError as exc:
                errors.append({"shipmentId": sid, "message": str(exc)})
        return {
            "total": len([i for i in shipment_ids if (i or "").strip()]),
            "subscribed": subscribed,
            "failed": len(errors),
            "errors": errors,
        }

    def unsubscribe(self, shipment_id: str) -> bool:
        sid = shipment_id.strip()
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {SUBSCRIPTIONS_TABLE} WHERE shipment_id = ?",
                (sid,),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def unsubscribe_many(self, shipment_ids: list[str]) -> dict[str, Any]:
        removed = 0
        for raw_id in shipment_ids:
            sid = (raw_id or "").strip()
            if sid and self.unsubscribe(sid):
                removed += 1
        return {
            "total": len([i for i in shipment_ids if (i or "").strip()]),
            "unsubscribed": removed,
        }

    def delete_for_shipment(self, shipment_id: str) -> None:
        sid = shipment_id.strip()
        with self._database.lock:
            self._conn.execute(
                f"DELETE FROM {SUBSCRIPTIONS_TABLE} WHERE shipment_id = ?",
                (sid,),
            )
            self._conn.commit()

    def maybe_notify_tracking(
        self,
        *,
        shipment_id: str,
        shipment_no: str,
        vessel_voyage: str,
        destination_port_code: str,
        source: TrackingSource,
        old_time: str | None,
        old_desc: str | None,
        new_time: str | None,
        new_desc: str | None,
        commit: bool = True,
    ) -> None:
        new_t = (new_time or "").strip()
        if not new_t:
            return
        old_t = (old_time or "").strip()
        old_d = (old_desc or "").strip()
        new_d = (new_desc or "").strip()
        if old_t == new_t and old_d == new_d:
            return
        with self._database.lock:
            sub = self._conn.execute(
                f"""
                SELECT id, last_notified_internal_time, last_notified_carrier_time
                FROM {SUBSCRIPTIONS_TABLE}
                WHERE shipment_id = ?
                """,
                (shipment_id,),
            ).fetchone()
            if sub is None:
                return
            last_col = (
                "last_notified_internal_time"
                if source == "internal"
                else "last_notified_carrier_time"
            )
            if (sub[last_col] or "").strip() == new_t:
                return
            self._create_tracking_notification_locked(
                subscription_id=sub["id"],
                shipment_id=shipment_id,
                shipment_no=shipment_no,
                vessel_voyage=vessel_voyage,
                destination_port_code=destination_port_code,
                source=source,
                latest_time=new_t,
                latest_desc=new_d,
            )
            self._conn.execute(
                f"""
                UPDATE {SUBSCRIPTIONS_TABLE}
                SET {last_col} = ?
                WHERE id = ?
                """,
                (new_t, sub["id"]),
            )
            if commit:
                self._conn.commit()

    def _create_tracking_notification_locked(
        self,
        *,
        subscription_id: str,
        shipment_id: str,
        shipment_no: str,
        vessel_voyage: str,
        destination_port_code: str,
        source: TrackingSource,
        latest_time: str,
        latest_desc: str,
    ) -> None:
        now = now_str()
        self._conn.execute(
            f"""
            INSERT INTO {NOTIFICATIONS_TABLE} (
                id, subscription_id, shipment_id, shipment_no,
                vessel_voyage, destination_port_code, ata,
                tracking_source, latest_time, latest_desc,
                created_at, read_at
            ) VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, '')
            """,
            (
                str(uuid.uuid4()),
                subscription_id,
                shipment_id,
                shipment_no,
                vessel_voyage,
                destination_port_code,
                source,
                latest_time,
                latest_desc,
                now,
            ),
        )

    def count_unread_notifications(self) -> int:
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {NOTIFICATIONS_TABLE}
                WHERE TRIM(COALESCE(read_at, '')) = ''
                """
            ).fetchone()
        return int(row["c"]) if row else 0

    def list_unread_notifications(self, *, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT n.*, s.customer AS shipment_customer
                FROM {NOTIFICATIONS_TABLE} n
                LEFT JOIN {SHIPMENTS_TABLE} s ON s.id = n.shipment_id
                WHERE TRIM(COALESCE(n.read_at, '')) = ''
                ORDER BY datetime(n.created_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_notification_to_api(r) for r in rows]

    def mark_notification_read(self, notification_id: str) -> bool:
        nid = notification_id.strip()
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {NOTIFICATIONS_TABLE}
                SET read_at = ?
                WHERE id = ? AND TRIM(COALESCE(read_at, '')) = ''
                """,
                (now, nid),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def mark_all_notifications_read(self) -> int:
        now = now_str()
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {NOTIFICATIONS_TABLE}
                SET read_at = ?
                WHERE TRIM(COALESCE(read_at, '')) = ''
                """,
                (now,),
            )
            self._conn.commit()
            return cur.rowcount
