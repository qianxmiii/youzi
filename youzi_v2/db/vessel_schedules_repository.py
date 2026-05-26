"""航次船期 CRUD 与运单关联。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from .datetime_util import normalize_tracking_time, now_str
from .shipments_repository import ShipmentsRepository
from .vessel_voyages_table import PORT_CALLS_TABLE, VOYAGES_TABLE
from ..services.voyage_status import enrich_port_call, enrich_shipment, summarize_shipment_statuses

SHIPMENTS_TABLE = "shipments"


def _normalize_vessel_voyage(value: str) -> str:
    return value.strip()


def _normalize_time(value: str | None) -> str | None:
    if value is None:
        return None
    text = normalize_tracking_time(value)
    return text or None


def _port_row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "voyageId": row["voyage_id"],
        "portName": row["port_name"],
        "sequence": row["sequence"],
        "eta": row["eta"],
        "ata": row["ata"],
        "etd": row["etd"],
        "atd": row["atd"],
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


def _voyage_row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "vesselVoyage": row["vessel_voyage"],
        "notes": row["notes"] or "",
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


class VesselSchedulesRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _get_by_vessel_voyage(self, vessel_voyage: str) -> dict[str, Any] | None:
        vv = _normalize_vessel_voyage(vessel_voyage)
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {VOYAGES_TABLE} WHERE vessel_voyage = ? COLLATE NOCASE",
                (vv,),
            ).fetchone()
        return _voyage_row_to_api(row) if row else None

    def _fetch_port_calls(self, voyage_id: str) -> list[dict[str, Any]]:
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM {PORT_CALLS_TABLE}
                WHERE voyage_id = ?
                ORDER BY sequence ASC, created_time ASC
                """,
                (voyage_id,),
            ).fetchall()
        return [enrich_port_call(_port_row_to_api(r)) for r in rows]

    def _shipment_count(self, vessel_voyage: str) -> int:
        vv = _normalize_vessel_voyage(vessel_voyage)
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT COUNT(*) AS c FROM {SHIPMENTS_TABLE}
                WHERE TRIM(vessel_voyage) != ''
                  AND vessel_voyage = ? COLLATE NOCASE
                """,
                (vv,),
            ).fetchone()
        return int(row["c"] or 0)

    def list_rows(
        self,
        *,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        conditions: list[str] = []
        params: list[Any] = []
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append("(vessel_voyage LIKE ? OR notes LIKE ?)")
            params.extend([q, q])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {VOYAGES_TABLE} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT v.*,
                       (SELECT COUNT(*) FROM {PORT_CALLS_TABLE} p WHERE p.voyage_id = v.id) AS port_count
                FROM {VOYAGES_TABLE} v
                {where}
                ORDER BY datetime(v.updated_time) DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        items = []
        for row in rows:
            api = _voyage_row_to_api(row)
            api["portCount"] = int(row["port_count"] or 0)
            api["shipmentCount"] = self._shipment_count(api["vesselVoyage"])
            items.append(api)
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_detail(self, voyage_id: str) -> dict[str, Any] | None:
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {VOYAGES_TABLE} WHERE id = ?",
                (voyage_id.strip(),),
            ).fetchone()
        if not row:
            return None
        api = _voyage_row_to_api(row)
        api["portCalls"] = self._fetch_port_calls(api["id"])
        api["shipmentCount"] = self._shipment_count(api["vesselVoyage"])
        shipments = self.list_shipments_for_voyage(
            api["vesselVoyage"],
            limit=500,
            offset=0,
        )
        api["shipmentSummary"] = summarize_shipment_statuses(shipments.get("items") or [])
        return api

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        vv = _normalize_vessel_voyage(str(data.get("vessel_voyage") or data.get("vesselVoyage") or ""))
        if not vv:
            raise ValueError("船名航次不能为空")
        if self._get_by_vessel_voyage(vv):
            raise ValueError(f"航次已存在: {vv}")
        voyage_id = str(uuid.uuid4())
        now = now_str()
        notes = str(data.get("notes") or "").strip()
        port_calls = data.get("port_calls") or data.get("portCalls") or []
        with self._database.lock:
            self._conn.execute(
                f"""
                INSERT INTO {VOYAGES_TABLE} (id, vessel_voyage, notes, created_time, updated_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (voyage_id, vv, notes, now, now),
            )
            self._replace_port_calls_locked(voyage_id, port_calls, now)
            self._conn.commit()
        detail = self.get_detail(voyage_id)
        assert detail is not None
        return detail

    def update(self, voyage_id: str, data: dict[str, Any]) -> dict[str, Any]:
        vid = voyage_id.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {VOYAGES_TABLE} WHERE id = ?",
                (vid,),
            ).fetchone()
        if not row:
            raise ValueError("航次不存在")
        now = now_str()
        vv = row["vessel_voyage"]
        notes = row["notes"]
        if "vessel_voyage" in data or "vesselVoyage" in data:
            new_vv = _normalize_vessel_voyage(
                str(data.get("vessel_voyage") or data.get("vesselVoyage") or "")
            )
            if not new_vv:
                raise ValueError("船名航次不能为空")
            existing = self._get_by_vessel_voyage(new_vv)
            if existing and existing["id"] != vid:
                raise ValueError(f"航次已存在: {new_vv}")
            vv = new_vv
        if "notes" in data and data["notes"] is not None:
            notes = str(data["notes"]).strip()
        port_calls = data.get("port_calls") if "port_calls" in data else data.get("portCalls")
        with self._database.lock:
            self._conn.execute(
                f"""
                UPDATE {VOYAGES_TABLE}
                SET vessel_voyage = ?, notes = ?, updated_time = ?
                WHERE id = ?
                """,
                (vv, notes, now, vid),
            )
            if port_calls is not None:
                self._replace_port_calls_locked(vid, port_calls, now)
            self._conn.commit()
        detail = self.get_detail(vid)
        assert detail is not None
        return detail

    def delete(self, voyage_id: str) -> None:
        vid = voyage_id.strip()
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {VOYAGES_TABLE} WHERE id = ?",
                (vid,),
            )
            self._conn.execute(
                f"DELETE FROM {PORT_CALLS_TABLE} WHERE voyage_id = ?",
                (vid,),
            )
            self._conn.commit()
        if cur.rowcount == 0:
            raise ValueError("航次不存在")

    def upsert_from_import(
        self,
        *,
        vessel_voyage: str,
        port_calls: list[dict[str, Any]],
        notes: str = "",
    ) -> tuple[dict[str, Any], bool]:
        vv = _normalize_vessel_voyage(vessel_voyage)
        if not vv:
            raise ValueError("船名航次不能为空")
        existing = self._get_by_vessel_voyage(vv)
        if existing:
            detail = self.update(
                existing["id"],
                {"vessel_voyage": vv, "notes": notes, "port_calls": port_calls},
            )
            return detail, False
        detail = self.create({"vessel_voyage": vv, "notes": notes, "port_calls": port_calls})
        return detail, True

    def list_shipments_for_voyage(
        self,
        vessel_voyage: str,
        *,
        maritime_status: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        vv = _normalize_vessel_voyage(vessel_voyage)
        repo = ShipmentsRepository(self._database)
        result = repo.list_rows(vessel_voyage=vv, limit=limit, offset=offset)
        enriched = [enrich_shipment(item) for item in result.get("items") or []]
        if maritime_status and maritime_status.strip():
            code = maritime_status.strip()
            enriched = [x for x in enriched if x.get("maritimeStatus") == code]
            return {
                "items": enriched,
                "total": len(enriched),
                "limit": limit,
                "offset": offset,
            }
        result["items"] = enriched
        return result

    def _replace_port_calls_locked(
        self,
        voyage_id: str,
        port_calls: list[dict[str, Any]],
        now: str,
    ) -> None:
        self._conn.execute(
            f"DELETE FROM {PORT_CALLS_TABLE} WHERE voyage_id = ?",
            (voyage_id,),
        )
        for idx, pc in enumerate(port_calls, start=1):
            port_name = str(pc.get("port_name") or pc.get("portName") or "").strip()
            if not port_name:
                continue
            seq_raw = pc.get("sequence")
            try:
                sequence = int(seq_raw) if seq_raw is not None else idx
            except (TypeError, ValueError):
                sequence = idx
            self._conn.execute(
                f"""
                INSERT INTO {PORT_CALLS_TABLE} (
                    id, voyage_id, port_name, sequence,
                    eta, ata, etd, atd, created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(pc.get("id") or uuid.uuid4()),
                    voyage_id,
                    port_name,
                    max(1, sequence),
                    _normalize_time(pc.get("eta")),
                    _normalize_time(pc.get("ata")),
                    _normalize_time(pc.get("etd")),
                    _normalize_time(pc.get("atd")),
                    now,
                    now,
                ),
            )
