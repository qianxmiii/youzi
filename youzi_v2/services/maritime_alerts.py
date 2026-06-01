"""首页海运预警聚合。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.port_subscriptions_table import PortSubscriptionsRepository
from youzi_v2.db.shipment_subscriptions_table import ShipmentSubscriptionsRepository
from youzi_v2.db.vessel_voyages_table import PORT_CALLS_TABLE, VOYAGES_TABLE
from youzi_v2.services.voyage_status import (
    enrich_port_call,
    enrich_shipment,
    status_label,
    summarize_shipment_statuses,
)

SHIPMENTS_TABLE = "shipments"
_URGENT_LIMIT = 8
_VOYAGE_ALERT_LIMIT = 6


def _sort_key_eta_etd(item: dict[str, Any]) -> str:
    return item.get("eta") or item.get("etd") or item.get("ata") or item.get("atd") or "9999"


def build_maritime_alerts_overview(database: Database) -> dict[str, Any]:
    now = datetime.now()
    conn = database.conn

    with database.lock:
        shipment_rows = conn.execute(
            f"""
            SELECT shipment_no, customer, customer_no, vessel_voyage,
                   eta, ata, etd, atd, origin_port_code, destination_port_code,
                   status_code
            FROM {SHIPMENTS_TABLE}
            WHERE (
                TRIM(COALESCE(vessel_voyage, '')) != ''
                OR TRIM(COALESCE(eta, '')) != ''
                OR TRIM(COALESCE(etd, '')) != ''
                OR TRIM(COALESCE(atd, '')) != ''
                OR TRIM(COALESCE(ata, '')) != ''
            )
            ORDER BY datetime(updated_time) DESC
            LIMIT 3000
            """
        ).fetchall()

        port_rows = conn.execute(
            f"""
            SELECT p.*, v.vessel_voyage AS voyage_vessel_voyage, v.id AS voyage_id
            FROM {PORT_CALLS_TABLE} p
            JOIN {VOYAGES_TABLE} v ON v.id = p.voyage_id
            ORDER BY v.vessel_voyage ASC, p.sequence ASC
            """
        ).fetchall()

    enriched_shipments: list[dict[str, Any]] = []
    for row in shipment_rows:
        item = {
            "shipmentNo": row["shipment_no"],
            "customer": row["customer"],
            "customerNo": row["customer_no"],
            "vesselVoyage": row["vessel_voyage"],
            "eta": row["eta"],
            "ata": row["ata"],
            "etd": row["etd"],
            "atd": row["atd"],
            "originPortCode": row["origin_port_code"],
            "destinationPortCode": row["destination_port_code"],
            "statusCode": row["status_code"],
        }
        enriched_shipments.append(enrich_shipment(item, now=now))

    counts = summarize_shipment_statuses(enriched_shipments)
    counts["portArrivingSoon"] = 0
    counts["portDepartingSoon"] = 0

    urgent_port_calls: list[dict[str, Any]] = []
    voyage_alert_map: dict[str, dict[str, Any]] = {}

    for row in port_rows:
        pc = enrich_port_call(
            {
                "id": row["id"],
                "voyageId": row["voyage_id"],
                "portName": row["port_name"],
                "sequence": row["sequence"],
                "eta": row["eta"],
                "ata": row["ata"],
                "etd": row["etd"],
                "atd": row["atd"],
            },
            now=now,
        )
        status = pc.get("status") or ""
        vv = row["voyage_vessel_voyage"]
        if status == "arriving_soon":
            counts["portArrivingSoon"] += 1
        elif status == "departing_soon":
            counts["portDepartingSoon"] += 1

        if status in ("arriving_soon", "departing_soon"):
            urgent_port_calls.append(
                {
                    "voyageId": row["voyage_id"],
                    "vesselVoyage": vv,
                    "portName": pc["portName"],
                    "sequence": pc["sequence"],
                    "status": status,
                    "statusLabel": pc.get("statusLabel") or status_label(status),
                    "eta": pc.get("eta"),
                    "etd": pc.get("etd"),
                }
            )
            bucket = voyage_alert_map.setdefault(
                row["voyage_id"],
                {
                    "voyageId": row["voyage_id"],
                    "vesselVoyage": vv,
                    "arrivingSoonPorts": 0,
                    "departingSoonPorts": 0,
                },
            )
            if status == "arriving_soon":
                bucket["arrivingSoonPorts"] += 1
            else:
                bucket["departingSoonPorts"] += 1

    urgent_statuses = {"arriving_soon", "departing_soon", "in_transit"}
    urgent_shipments = [
        s
        for s in enriched_shipments
        if (s.get("maritimeStatus") or "") in urgent_statuses
    ]
    urgent_shipments.sort(key=_sort_key_eta_etd)
    urgent_port_calls.sort(key=lambda x: _sort_key_eta_etd(x))

    eta_arriving_soon_port_calls = [
        pc
        for pc in urgent_port_calls
        if pc.get("status") == "arriving_soon"
    ]
    eta_arriving_soon_shipments = [
        s
        for s in enriched_shipments
        if (s.get("maritimeStatus") or "") == "arriving_soon"
    ]
    eta_arriving_soon_shipments.sort(key=_sort_key_eta_etd)

    voyages_with_alerts = sorted(
        voyage_alert_map.values(),
        key=lambda v: -(v["arrivingSoonPorts"] + v["departingSoonPorts"]),
    )[:_VOYAGE_ALERT_LIMIT]

    # 有预警挂靠但未配置航次主数据的 vessel_voyage（仅运单侧有船期）
    configured_vv = {r["voyage_vessel_voyage"].lower() for r in port_rows}
    orphan_vv: dict[str, int] = {}
    for s in enriched_shipments:
        if (s.get("maritimeStatus") or "") not in urgent_statuses:
            continue
        vv = (s.get("vesselVoyage") or "").strip()
        if vv and vv.lower() not in configured_vv:
            orphan_vv[vv] = orphan_vv.get(vv, 0) + 1

    return {
        "generatedAt": now_str(),
        "counts": counts,
        "urgentShipments": urgent_shipments[:_URGENT_LIMIT],
        "urgentPortCalls": urgent_port_calls[:_URGENT_LIMIT],
        "etaArrivingSoonPortCalls": eta_arriving_soon_port_calls[:20],
        "etaArrivingSoonShipments": eta_arriving_soon_shipments[:20],
        "voyagesWithAlerts": voyages_with_alerts,
        "unconfiguredVesselVoyages": [
            {"vesselVoyage": k, "shipmentCount": v}
            for k, v in sorted(orphan_vv.items(), key=lambda x: -x[1])[:5]
        ],
        "totalScanned": len(enriched_shipments),
        "portArrivalNotifications": PortSubscriptionsRepository(
            database
        ).list_unread_notifications(limit=20),
        "shipmentArrivalNotifications": ShipmentSubscriptionsRepository(
            database
        ).list_unread_notifications(limit=20),
    }
