"""按 waybillId 拉取 DPS 明细状态轨迹，回写 route_status（轻量，非整单）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..db.datetime_util import normalize_tracking_time
from ..db.shipment_route_status import map_dps_route_status
from ..db.shipment_sla import (
    SLA_DELIVERED_ROUTE_STATUS,
    SLA_FIELD_ARRIVED_POD_TIME,
    SLA_FIELD_DEST_TRANSIT_TIME,
    SLA_FIELD_WAREHOUSE_IN_TIME,
)
from ..db.shipments_repository import ShipmentsRepository
from .dps_waybill_route_info import query_waybill_route_info
from .shipment_route_status_exception import apply_customs_exception_from_route_status
from .shipment_sla_scan import maybe_resolve_alerts_after_delivery

LogFn = Callable[[str], None]

# 异常跟踪阶段卡点起算：取各明细状态首次出现的 nodeTime
_ROUTE_MILESTONE_TIME_FIELDS: dict[str, str] = {
    "WAREHOUSE_IN": SLA_FIELD_WAREHOUSE_IN_TIME,
    "ARRIVED_POD": SLA_FIELD_ARRIVED_POD_TIME,
    "DEST_TRANSIT_WAREHOUSE": SLA_FIELD_DEST_TRANSIT_TIME,
}


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def pick_latest_milestone_from_nodes(
    nodes: list[dict[str, Any]],
) -> tuple[str | None, dict[str, Any] | None]:
    """按 nodeTime 倒序取首个可映射的关键明细状态；返回 (route_status, 该节点)。"""
    ranked = sorted(
        nodes,
        key=lambda n: normalize_tracking_time(str(n.get("nodeTime") or ""))
        or str(n.get("nodeTime") or ""),
        reverse=True,
    )
    for node in ranked:
        code = map_dps_route_status(node.get("status"))
        if code:
            return code, node
    return None, ranked[0] if ranked else None


def pick_latest_node(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not nodes:
        return None
    return max(
        nodes,
        key=lambda n: normalize_tracking_time(str(n.get("nodeTime") or ""))
        or str(n.get("nodeTime") or ""),
    )


def extract_route_milestone_times(nodes: list[dict[str, Any]]) -> dict[str, str]:
    """从节点列表提取 202/306/502 等关键节点的最早时间 → 本地字段。"""
    earliest: dict[str, str] = {}
    for node in nodes:
        code = map_dps_route_status(node.get("status"))
        if not code or code not in _ROUTE_MILESTONE_TIME_FIELDS:
            continue
        raw_time = normalize_tracking_time(str(node.get("nodeTime") or ""))
        if not raw_time:
            continue
        prev = earliest.get(code)
        if prev is None or raw_time < prev:
            earliest[code] = raw_time
    return {
        _ROUTE_MILESTONE_TIME_FIELDS[code]: time
        for code, time in earliest.items()
    }


def sync_route_status_by_waybill_ids(
    shipments_repo: ShipmentsRepository,
    config_path: Path,
    shipment_nos: list[str] | None = None,
    *,
    log: LogFn | None = None,
) -> dict[str, Any]:
    """
    对本地已有 waybill_id 的运单调用 config 中的明细状态接口，更新 route_status，
    并联动清关异常；可选回写预计送仓 / 最新轨迹摘要。

    shipment_nos 为 None / 空：同步全部有 waybill_id 的运单。
    """

    def out(msg: str) -> None:
        if log:
            log(msg)

    if shipment_nos:
        nos = list(dict.fromkeys(n.strip() for n in shipment_nos if n and n.strip()))
    else:
        nos = shipments_repo.list_shipment_nos_with_waybill_id()
    total = len(nos)
    updated = 0
    unchanged = 0
    skipped_no_waybill = 0
    skipped_no_waybill_nos: list[str] = []
    empty = 0
    failed = 0
    customs_opened = 0
    customs_closed = 0
    errors: list[str] = []
    not_local = 0

    out(f"[DPS明细状态] 开始，共 {total} 单")

    for sn in nos:
        ship = shipments_repo.get_by_shipment_no(sn)
        if ship is None:
            not_local += 1
            failed += 1
            if len(errors) < 20:
                errors.append(f"{sn}: 本地无此运单")
            continue

        waybill_id = _opt_str(ship.get("waybillId"))
        if not waybill_id:
            skipped_no_waybill += 1
            skipped_no_waybill_nos.append(sn)
            continue

        try:
            nodes = query_waybill_route_info(config_path, waybill_id)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            if len(errors) < 20:
                errors.append(f"{sn}: {exc}")
            out(f"[DPS明细状态] 失败 {sn}: {exc}")
            continue

        if not nodes:
            empty += 1
            out(f"[DPS明细状态] {sn} 接口无节点")
            continue

        route_status, milestone_node = pick_latest_milestone_from_nodes(nodes)
        latest = pick_latest_node(nodes) or {}
        prev_route = _opt_str(ship.get("routeStatus"))
        patch: dict[str, Any] = {}

        if route_status and route_status != prev_route:
            patch["route_status"] = route_status

        for field, time_val in extract_route_milestone_times(nodes).items():
            camel = {
                SLA_FIELD_WAREHOUSE_IN_TIME: "routeWarehouseInTime",
                SLA_FIELD_ARRIVED_POD_TIME: "routeArrivedPodTime",
                SLA_FIELD_DEST_TRANSIT_TIME: "routeDestTransitWarehouseTime",
            }[field]
            if time_val != _opt_str(ship.get(camel)):
                patch[field] = time_val

        edd = _opt_str(
            (milestone_node or {}).get("estimatedDeliveryDate")
        ) or _opt_str(latest.get("estimatedDeliveryDate"))
        if edd and edd != _opt_str(ship.get("expectedDeliveryTime")):
            patch["expected_delivery_time"] = edd

        latest_time = normalize_tracking_time(str(latest.get("nodeTime") or "")) or None
        latest_desc = _opt_str(latest.get("nodeDesc"))
        if latest_time and latest_desc:
            if latest_time != _opt_str(
                ship.get("latestTrackingTime")
            ) or latest_desc != _opt_str(ship.get("latestTrackingDesc")):
                patch["latest_tracking_time"] = latest_time
                patch["latest_tracking_desc"] = latest_desc

        if patch:
            shipments_repo.update_row(ship["id"], patch)
            updated += 1
            out(
                f"[DPS明细状态] {sn} waybillId={waybill_id} "
                f"route_status={route_status or prev_route or '—'}"
            )
        else:
            unchanged += 1

        route_for_exc = route_status or prev_route
        exc_result = apply_customs_exception_from_route_status(
            shipments_repo._database,
            sn,
            route_for_exc,
        )
        if exc_result.get("action") == "opened":
            customs_opened += 1
        elif exc_result.get("action") == "closed":
            customs_closed += 1

        if (route_for_exc or "").strip().upper() == SLA_DELIVERED_ROUTE_STATUS:
            maybe_resolve_alerts_after_delivery(
                shipments_repo._database,
                ship["id"],
                shipment_no=sn,
                log=out,
            )

    out(
        f"[DPS明细状态] 结束：更新 {updated}，无变化 {unchanged}，"
        f"无 waybillId {skipped_no_waybill}，空轨迹 {empty}，失败 {failed}"
    )

    return {
        "total": total,
        "updated": updated,
        "unchanged": unchanged,
        "empty": empty,
        "failed": failed,
        "notLocal": not_local,
        "missingWaybillId": skipped_no_waybill,
        "missingWaybillIdNos": skipped_no_waybill_nos[:50],
        "customsExceptionOpened": customs_opened,
        "customsExceptionClosed": customs_closed,
        "errors": errors,
    }
