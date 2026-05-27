"""航次船期 CRUD 与运单关联。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from .datetime_util import normalize_tracking_time, now_str
from .shipments_repository import ShipmentsRepository
from .vessel_voyages_table import PORT_CALLS_TABLE, VOYAGES_TABLE
from ..services.port_code_resolve import PortCodeResolver
from ..services.vessel_voyage_fields import resolve_voyage_identity, shipment_voyage_match_sql
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


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _extract_voyage_meta(data: dict[str, Any]) -> dict[str, str | None]:
    vv, name, voyage = resolve_voyage_identity(
        vessel_voyage=data.get("vessel_voyage") or data.get("vesselVoyage"),
        vessel_name=data.get("vessel_name") or data.get("vesselName"),
        voyage_no=data.get("voyage_no") or data.get("voyageNo"),
    )
    return {
        "vessel_voyage": vv,
        "vessel_name": name,
        "voyage_no": voyage,
        "vessel_code": _optional_str(data.get("vessel_code") or data.get("vesselCode")),
        "shipping_company": _optional_str(
            data.get("shipping_company") or data.get("shippingCompany")
        ),
    }


def _voyage_row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "vesselVoyage": row["vessel_voyage"],
        "vesselName": row["vessel_name"],
        "voyageNo": row["voyage_no"],
        "vesselCode": row["vessel_code"],
        "shippingCompany": row["shipping_company"],
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

    def _get_by_carrier(
        self,
        shipping_company: str,
        vessel_code: str,
    ) -> dict[str, Any] | None:
        company = (shipping_company or "").strip()
        code = (vessel_code or "").strip().upper()
        if not company or not code:
            return None
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT * FROM {VOYAGES_TABLE}
                WHERE TRIM(COALESCE(shipping_company, '')) != ''
                  AND TRIM(COALESCE(vessel_code, '')) != ''
                  AND shipping_company = ? COLLATE NOCASE
                  AND UPPER(TRIM(vessel_code)) = ?
                ORDER BY datetime(updated_time) DESC
                LIMIT 1
                """,
                (company, code),
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
            resolver = PortCodeResolver(self._conn)
            return [
                resolver.enrich_port_call(enrich_port_call(_port_row_to_api(r)))
                for r in rows
            ]

    def _shipment_count(
        self,
        vessel_voyage: str,
        vessel_name: str | None = None,
        voyage_no: str | None = None,
    ) -> int:
        match_sql, match_params = shipment_voyage_match_sql(
            vessel_voyage, vessel_name, voyage_no
        )
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {SHIPMENTS_TABLE} WHERE {match_sql}",
                match_params,
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
            conditions.append(
                """(
                    vessel_voyage LIKE ? OR notes LIKE ? OR vessel_name LIKE ?
                    OR voyage_no LIKE ? OR vessel_code LIKE ? OR shipping_company LIKE ?
                )"""
            )
            params.extend([q, q, q, q, q, q])
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
            api["shipmentCount"] = self._shipment_count(
                api["vesselVoyage"],
                api.get("vesselName"),
                api.get("voyageNo"),
            )
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
        api["shipmentCount"] = self._shipment_count(
            api["vesselVoyage"],
            api.get("vesselName"),
            api.get("voyageNo"),
        )
        shipments = self.list_shipments_for_voyage(
            api["vesselVoyage"],
            vessel_name=api.get("vesselName"),
            voyage_no=api.get("voyageNo"),
            limit=500,
            offset=0,
        )
        api["shipmentSummary"] = summarize_shipment_statuses(shipments.get("items") or [])
        return api

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        meta = _extract_voyage_meta(data)
        vv = _normalize_vessel_voyage(meta["vessel_voyage"] or "")
        existing = self._get_by_vessel_voyage(vv)
        if existing:
            return self.update(existing["id"], data)
        voyage_id = str(uuid.uuid4())
        now = now_str()
        notes = str(data.get("notes") or "").strip()
        port_calls = data.get("port_calls") or data.get("portCalls") or []
        with self._database.lock:
            self._conn.execute(
                f"""
                INSERT INTO {VOYAGES_TABLE} (
                    id, vessel_voyage, vessel_name, voyage_no, vessel_code,
                    shipping_company, notes, created_time, updated_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    voyage_id,
                    vv,
                    meta["vessel_name"],
                    meta["voyage_no"],
                    meta["vessel_code"],
                    meta["shipping_company"],
                    notes,
                    now,
                    now,
                ),
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
        merge = {
            "vessel_voyage": data.get("vessel_voyage")
            if "vessel_voyage" in data
            else data.get("vesselVoyage")
            if "vesselVoyage" in data
            else row["vessel_voyage"],
            "vessel_name": data.get("vessel_name")
            if "vessel_name" in data
            else data.get("vesselName")
            if "vesselName" in data
            else row["vessel_name"],
            "voyage_no": data.get("voyage_no")
            if "voyage_no" in data
            else data.get("voyageNo")
            if "voyageNo" in data
            else row["voyage_no"],
            "vessel_code": data.get("vessel_code")
            if "vessel_code" in data
            else data.get("vesselCode")
            if "vesselCode" in data
            else row["vessel_code"],
            "shipping_company": data.get("shipping_company")
            if "shipping_company" in data
            else data.get("shippingCompany")
            if "shippingCompany" in data
            else row["shipping_company"],
        }
        meta = _extract_voyage_meta(merge)
        vv = _normalize_vessel_voyage(meta["vessel_voyage"] or "")
        existing = self._get_by_vessel_voyage(vv)
        if existing and existing["id"] != vid:
            raise ValueError(f"航次已存在: {vv}")
        notes = row["notes"]
        if "notes" in data and data["notes"] is not None:
            notes = str(data["notes"]).strip()
        port_calls = data.get("port_calls") if "port_calls" in data else data.get("portCalls")
        with self._database.lock:
            self._conn.execute(
                f"""
                UPDATE {VOYAGES_TABLE}
                SET vessel_voyage = ?, vessel_name = ?, voyage_no = ?,
                    vessel_code = ?, shipping_company = ?, notes = ?, updated_time = ?
                WHERE id = ?
                """,
                (
                    vv,
                    meta["vessel_name"],
                    meta["voyage_no"],
                    meta["vessel_code"],
                    meta["shipping_company"],
                    notes,
                    now,
                    vid,
                ),
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
        vessel_name: str | None = None,
        voyage_no: str | None = None,
        vessel_code: str | None = None,
        shipping_company: str | None = None,
        match_by_carrier: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        payload = {
            "vessel_voyage": vessel_voyage,
            "vessel_name": vessel_name,
            "voyage_no": voyage_no,
            "vessel_code": vessel_code,
            "shipping_company": shipping_company,
            "notes": notes,
            "port_calls": port_calls,
        }
        meta = _extract_voyage_meta(payload)
        vv = _normalize_vessel_voyage(meta["vessel_voyage"] or "")
        existing: dict[str, Any] | None = None
        if match_by_carrier and meta.get("shipping_company") and meta.get("vessel_code"):
            existing = self._get_by_carrier(
                str(meta["shipping_company"]),
                str(meta["vessel_code"]),
            )
        if not existing:
            existing = self._get_by_vessel_voyage(vv)
        if existing:
            detail = self.update(existing["id"], payload)
            return detail, False
        detail = self.create(payload)
        return detail, True

    def list_shipments_for_voyage(
        self,
        vessel_voyage: str,
        *,
        vessel_name: str | None = None,
        voyage_no: str | None = None,
        maritime_status: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        repo = ShipmentsRepository(self._database)
        result = repo.list_rows(
            vessel_voyage=vessel_voyage,
            vessel_name=vessel_name,
            voyage_no=voyage_no,
            vessel_voyage_flexible=True,
            limit=limit,
            offset=offset,
        )
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
