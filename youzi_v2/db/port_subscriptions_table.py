"""挂靠港订阅与到港通知。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .vessel_voyages_table import PORT_CALLS_TABLE, VOYAGES_TABLE

SUBSCRIPTIONS_TABLE = "port_subscriptions"
NOTIFICATIONS_TABLE = "port_arrival_notifications"

_CREATE_SUBSCRIPTIONS_SQL = f"""
CREATE TABLE IF NOT EXISTS {SUBSCRIPTIONS_TABLE} (
    id TEXT PRIMARY KEY,
    port_call_id TEXT NOT NULL UNIQUE,
    voyage_id TEXT NOT NULL,
    port_name TEXT NOT NULL DEFAULT '',
    vessel_voyage TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    last_notified_ata TEXT NOT NULL DEFAULT ''
)
"""

_CREATE_NOTIFICATIONS_SQL = f"""
CREATE TABLE IF NOT EXISTS {NOTIFICATIONS_TABLE} (
    id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL,
    port_call_id TEXT NOT NULL,
    voyage_id TEXT NOT NULL,
    port_name TEXT NOT NULL DEFAULT '',
    vessel_voyage TEXT NOT NULL DEFAULT '',
    ata TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    read_at TEXT NOT NULL DEFAULT ''
)
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SUBSCRIPTIONS_SQL)
    conn.execute(_CREATE_NOTIFICATIONS_SQL)
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{SUBSCRIPTIONS_TABLE}_voyage
        ON {SUBSCRIPTIONS_TABLE}(voyage_id)
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{NOTIFICATIONS_TABLE}_unread
        ON {NOTIFICATIONS_TABLE}(read_at, created_at)
        """
    )


def _notification_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "subscriptionId": row["subscription_id"],
        "portCallId": row["port_call_id"],
        "voyageId": row["voyage_id"],
        "portName": row["port_name"],
        "vesselVoyage": row["vessel_voyage"],
        "ata": row["ata"],
        "createdAt": row["created_at"],
        "readAt": row["read_at"] or None,
    }


class PortSubscriptionsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def subscribed_port_call_ids(self) -> set[str]:
        with self._database.lock:
            rows = self._conn.execute(
                f"SELECT port_call_id FROM {SUBSCRIPTIONS_TABLE}"
            ).fetchall()
        return {str(r["port_call_id"]) for r in rows}

    def subscribe(self, port_call_id: str) -> dict[str, Any]:
        pc_id = port_call_id.strip()
        if not pc_id:
            raise ValueError("挂靠港 id 无效")
        with self._database.lock:
            pc = self._conn.execute(
                f"""
                SELECT p.*, v.vessel_voyage AS voyage_vessel_voyage
                FROM {PORT_CALLS_TABLE} p
                JOIN {VOYAGES_TABLE} v ON v.id = p.voyage_id
                WHERE p.id = ?
                """,
                (pc_id,),
            ).fetchone()
            if pc is None:
                raise KeyError(pc_id)

            existing = self._conn.execute(
                f"SELECT id FROM {SUBSCRIPTIONS_TABLE} WHERE port_call_id = ?",
                (pc_id,),
            ).fetchone()
            if existing:
                sub_id = existing["id"]
            else:
                sub_id = str(uuid.uuid4())
                now = now_str()
                self._conn.execute(
                    f"""
                    INSERT INTO {SUBSCRIPTIONS_TABLE} (
                        id, port_call_id, voyage_id, port_name, vessel_voyage, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sub_id,
                        pc_id,
                        pc["voyage_id"],
                        pc["port_name"],
                        pc["voyage_vessel_voyage"],
                        now,
                    ),
                )

            ata = (pc["ata"] or "").strip()
            if ata:
                self._create_notification_locked(
                    subscription_id=sub_id,
                    port_call_id=pc_id,
                    voyage_id=pc["voyage_id"],
                    port_name=pc["port_name"],
                    vessel_voyage=pc["voyage_vessel_voyage"],
                    ata=ata,
                )
            self._conn.commit()
        return {"subscribed": True, "portCallId": pc_id}

    def unsubscribe(self, port_call_id: str) -> bool:
        pc_id = port_call_id.strip()
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {SUBSCRIPTIONS_TABLE} WHERE port_call_id = ?",
                (pc_id,),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def maybe_notify_arrival(
        self,
        *,
        port_call_id: str,
        voyage_id: str,
        port_name: str,
        vessel_voyage: str,
        old_ata: str | None,
        new_ata: str | None,
        commit: bool = True,
    ) -> None:
        new_val = (new_ata or "").strip()
        if not new_val:
            return
        if (old_ata or "").strip() == new_val:
            return
        with self._database.lock:
            sub = self._conn.execute(
                f"""
                SELECT id FROM {SUBSCRIPTIONS_TABLE}
                WHERE port_call_id = ?
                """,
                (port_call_id,),
            ).fetchone()
            if sub is None:
                return
            self._create_notification_locked(
                subscription_id=sub["id"],
                port_call_id=port_call_id,
                voyage_id=voyage_id,
                port_name=port_name,
                vessel_voyage=vessel_voyage,
                ata=new_val,
            )
            if commit:
                self._conn.commit()

    def _create_notification_locked(
        self,
        *,
        subscription_id: str,
        port_call_id: str,
        voyage_id: str,
        port_name: str,
        vessel_voyage: str,
        ata: str,
    ) -> None:
        sub = self._conn.execute(
            f"SELECT last_notified_ata FROM {SUBSCRIPTIONS_TABLE} WHERE id = ?",
            (subscription_id,),
        ).fetchone()
        if sub and (sub["last_notified_ata"] or "").strip() == ata:
            return
        now = now_str()
        self._conn.execute(
            f"""
            INSERT INTO {NOTIFICATIONS_TABLE} (
                id, subscription_id, port_call_id, voyage_id,
                port_name, vessel_voyage, ata, created_at, read_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '')
            """,
            (
                str(uuid.uuid4()),
                subscription_id,
                port_call_id,
                voyage_id,
                port_name,
                vessel_voyage,
                ata,
                now,
            ),
        )
        self._conn.execute(
            f"""
            UPDATE {SUBSCRIPTIONS_TABLE}
            SET last_notified_ata = ?
            WHERE id = ?
            """,
            (ata, subscription_id),
        )

    def list_unread_notifications(self, *, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {NOTIFICATIONS_TABLE}
                WHERE TRIM(COALESCE(read_at, '')) = ''
                ORDER BY datetime(created_at) DESC
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
