"""运单分组推荐：按业务字段聚类，供用户确认后落库。"""

from __future__ import annotations

from typing import Any

from ..db.connection import Database
from ..db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from ..shipment_group_types import normalize_types_payload

_RULE_LABELS: dict[str, str] = {
    "CUSTOMER_ORDER": "同客户 + 客户订单号",
    "CUSTOMER_VESSEL": "同客户 + 船名航次",
    "CUSTOMER_PORT_ETA": "同客户 + 目的港 + ETA",
    "AMAZON_REF": "同亚马逊预约号",
    "CUSTOMER_SHIPMENT": "同货件号",
}

_GROUP_TYPES: dict[str, str] = {
    "CUSTOMER_ORDER": "ORDER_BATCH",
    "CUSTOMER_VESSEL": "VESSEL_BATCH",
    "CUSTOMER_PORT_ETA": "PORT_BATCH",
    "AMAZON_REF": "ORDER_BATCH",
    "CUSTOMER_SHIPMENT": "ORDER_BATCH",
}


def _norm(value: str | None) -> str:
    return (value or "").strip()


def _shipment_row_to_dict(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "shipmentNo": row["shipment_no"],
        "customer": row["customer"],
        "customerNo": row["customer_no"],
        "vesselVoyage": row["vessel_voyage"],
        "destinationPortCode": row["destination_port_code"],
        "eta": row["eta"],
        "amazonRefId": row["amazon_ref_id"],
        "customerShipmentId": row["customer_shipment_id"],
    }


def _cluster_key(rule_type: str, ship: dict[str, Any]) -> str | None:
    customer = _norm(ship.get("customer"))
    if rule_type == "CUSTOMER_ORDER":
        cn = _norm(ship.get("customerNo"))
        if customer and cn:
            return f"{customer}\0{cn}"
    elif rule_type == "CUSTOMER_VESSEL":
        vv = _norm(ship.get("vesselVoyage"))
        if customer and vv:
            return f"{customer}\0{vv}"
    elif rule_type == "CUSTOMER_PORT_ETA":
        port = _norm(ship.get("destinationPortCode"))
        eta = _norm(ship.get("eta"))
        if customer and port and eta:
            return f"{customer}\0{port}\0{eta}"
    elif rule_type == "AMAZON_REF":
        ref = _norm(ship.get("amazonRefId"))
        if ref:
            return ref
    elif rule_type == "CUSTOMER_SHIPMENT":
        csid = _norm(ship.get("customerShipmentId"))
        if csid:
            return csid
    return None


def _proposed_group_name(rule_type: str, key: str, sample: dict[str, Any]) -> str:
    customer = _norm(sample.get("customer"))
    if rule_type == "CUSTOMER_ORDER":
        return f"{customer} · {sample.get('customerNo') or ''}".strip(" ·")
    if rule_type == "CUSTOMER_VESSEL":
        return f"{customer} · {sample.get('vesselVoyage') or ''}".strip(" ·")
    if rule_type == "CUSTOMER_PORT_ETA":
        return (
            f"{customer} · {sample.get('destinationPortCode') or ''} · "
            f"{(sample.get('eta') or '')[:10]}"
        ).strip(" ·")
    if rule_type == "AMAZON_REF":
        return f"Amazon {key[:24]}"
    if rule_type == "CUSTOMER_SHIPMENT":
        return f"货件 {key[:24]}"
    return customer or "推荐分组"


def build_group_suggestions(
    database: Database,
    shipment_ids: list[str],
) -> dict[str, Any]:
    ids = list(dict.fromkeys(s.strip() for s in shipment_ids if s and s.strip()))
    if not ids:
        return {"suggestions": [], "shipmentCount": 0}

    placeholders = ", ".join("?" * len(ids))
    with database.lock:
        rows = database.conn.execute(
            f"""
            SELECT id, shipment_no, customer, customer_no, vessel_voyage,
                   destination_port_code, eta, amazon_ref_id, customer_shipment_id
            FROM {SHIPMENTS_TABLE}
            WHERE id IN ({placeholders})
            """,
            ids,
        ).fetchall()

    shipments = [_shipment_row_to_dict(r) for r in rows]
    found_ids = {s["id"] for s in shipments}
    missing = [sid for sid in ids if sid not in found_ids]

    suggestions: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for rule_type in _RULE_LABELS:
        buckets: dict[str, list[dict[str, Any]]] = {}
        for ship in shipments:
            key = _cluster_key(rule_type, ship)
            if not key:
                continue
            buckets.setdefault(key, []).append(ship)

        for key, members in buckets.items():
            if len(members) < 2:
                continue
            suggestion_key = f"{rule_type}|{key}"
            if suggestion_key in seen_keys:
                continue
            seen_keys.add(suggestion_key)
            sample = members[0]
            suggestions.append(
                {
                    "suggestionKey": suggestion_key,
                    "ruleType": rule_type,
                    "ruleLabel": _RULE_LABELS[rule_type],
                    "primaryType": _GROUP_TYPES[rule_type],
                    "groupTypes": [_GROUP_TYPES[rule_type]],
                    "groupType": _GROUP_TYPES[rule_type],
                    "proposedGroupName": _proposed_group_name(rule_type, key, sample),
                    "customer": _norm(sample.get("customer")) or None,
                    "customerNo": _norm(sample.get("customerNo")) or None,
                    "vesselVoyage": _norm(sample.get("vesselVoyage")) or None,
                    "destinationPortCode": _norm(sample.get("destinationPortCode")) or None,
                    "shipmentIds": [m["id"] for m in members],
                    "shipmentNos": [m["shipmentNo"] for m in members],
                    "memberCount": len(members),
                }
            )

    suggestions.sort(key=lambda s: (-int(s["memberCount"]), s["suggestionKey"]))
    return {
        "suggestions": suggestions,
        "shipmentCount": len(shipments),
        "missingShipmentIds": missing,
    }


def apply_group_suggestions(
    groups_repo,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    groups_created = 0
    members_added = 0
    skipped = 0
    errors: list[dict[str, str]] = []

    for item in items:
        ids = [
            s.strip()
            for s in (item.get("shipmentIds") or item.get("shipment_ids") or [])
            if s and str(s).strip()
        ]
        if not ids:
            skipped += 1
            continue
        try:
            group_no = (item.get("groupNo") or item.get("group_no") or "").strip()
            group_name = (item.get("groupName") or item.get("group_name") or item.get("proposedGroupName") or "").strip()
            primary, types = normalize_types_payload(
                primary_type=item.get("primaryType") or item.get("primary_type"),
                group_types=item.get("groupTypes") or item.get("group_types"),
                legacy_group_type=item.get("groupType") or item.get("group_type"),
            )
            if group_no:
                group, is_new = groups_repo.get_or_create_for_import(
                    group_no,
                    group_name=group_name,
                    primary_type=primary,
                    group_types=types,
                    customer=item.get("customer"),
                    customer_no=item.get("customerNo") or item.get("customer_no"),
                    vessel_voyage=item.get("vesselVoyage") or item.get("vessel_voyage"),
                    destination_port_code=item.get("destinationPortCode")
                    or item.get("destination_port_code"),
                )
            else:
                group = groups_repo.create(
                    group_name=group_name,
                    primary_type=primary,
                    group_types=types,
                    customer=item.get("customer"),
                    customer_no=item.get("customerNo") or item.get("customer_no"),
                    vessel_voyage=item.get("vesselVoyage") or item.get("vessel_voyage"),
                    destination_port_code=item.get("destinationPortCode")
                    or item.get("destination_port_code"),
                )
                is_new = True
            if is_new:
                groups_created += 1
            res = groups_repo.add_members(group["id"], ids)
            members_added += int(res.get("added") or 0)
        except Exception as exc:  # noqa: BLE001
            key = str(item.get("suggestionKey") or item.get("suggestion_key") or "")
            errors.append({"suggestionKey": key, "message": str(exc)})

    return {
        "groupsCreated": groups_created,
        "membersAdded": members_added,
        "skipped": skipped,
        "errors": errors,
    }