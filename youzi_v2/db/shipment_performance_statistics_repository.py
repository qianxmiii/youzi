"""运输时效统计：基于 ETD/ATD/ETA/ATA/预计送仓/签收时间聚合。"""

from __future__ import annotations

import csv
import io
import math
import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable

from ..schemas.shipment_performance_statistics import ShipmentPerformanceQuery
from .connection import Database
from .datetime_util import DATETIME_FMT, normalize_tracking_time
from .shipments_table import TABLE_NAME

MAX_ANALYSIS_ROWS = 20_000
POST_ARRIVAL_SLOW_DAYS = 7

DATE_BASIS_COLUMNS = {
    "atd": "atd",
    "ata": "ata",
    "signed_time": "delivered_time",
    "created_time": "created_time",
}

SORTABLE_DETAIL_FIELDS = {
    "shipmentNo": "shipment_no",
    "fullTransitDays": "full_transit_days",
    "seaTransitDays": "sea_transit_days",
    "postArrivalDays": "post_arrival_days",
    "deliveryDeviationDays": "delivery_deviation_days",
    "signedTime": "signed_time",
    "atd": "atd",
}


def _parse_date_only(raw: str | None) -> datetime | None:
    text = normalize_tracking_time(raw)
    if not text:
        return None
    for length, fmt in ((19, DATETIME_FMT), (16, "%Y-%m-%d %H:%M"), (10, "%Y-%m-%d")):
        try:
            return datetime.strptime(text[:length], fmt)
        except ValueError:
            continue
    return None


def _day_diff(end_raw: str | None, start_raw: str | None) -> int | None:
    end = _parse_date_only(end_raw)
    start = _parse_date_only(start_raw)
    if not end or not start:
        return None
    return (end.date() - start.date()).days


def _ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 1)
    k = (len(ordered) - 1) * (p / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return round(ordered[int(k)], 1)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo), 1)


def _metric_block(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "avgDays": None,
            "sampleCount": 0,
            "p50Days": None,
            "p90Days": None,
            "minDays": None,
            "maxDays": None,
        }
    return {
        "avgDays": round(sum(values) / len(values), 1),
        "sampleCount": len(values),
        "p50Days": _percentile(values, 50),
        "p90Days": _percentile(values, 90),
        "minDays": round(min(values), 1),
        "maxDays": round(max(values), 1),
    }


def _extreme_full_transit(
    items: list[dict[str, Any]],
) -> tuple[str | None, str | None, float | None, float | None]:
    fastest_no: str | None = None
    slowest_no: str | None = None
    min_days: float | None = None
    max_days: float | None = None
    for row in items:
        raw = row.get("full_transit_days")
        if raw is None:
            continue
        days = float(raw)
        if min_days is None or days < min_days:
            min_days = days
            fastest_no = row.get("shipment_no")
        if max_days is None or days > max_days:
            max_days = days
            slowest_no = row.get("shipment_no")
    return fastest_no, slowest_no, min_days, max_days


def _anomaly_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    eta_dev = row.get("eta_deviation_days")
    if eta_dev is not None and eta_dev > 0:
        flags.append("晚到港")
    delivery_dev = row.get("delivery_deviation_days")
    if delivery_dev is not None and delivery_dev > 0:
        flags.append("送仓晚于预计")
    post_arrival = row.get("post_arrival_days")
    if post_arrival is not None and post_arrival > POST_ARRIVAL_SLOW_DAYS:
        flags.append("到港后送仓过慢")
    return flags


class ShipmentPerformanceStatisticsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _normalize_query(self, params: ShipmentPerformanceQuery) -> ShipmentPerformanceQuery:
        basis = (params.date_basis or "atd").strip().lower()
        if basis not in DATE_BASIS_COLUMNS:
            basis = "atd"
        return ShipmentPerformanceQuery(
            date_from=(params.date_from or "").strip() or None,
            date_to=(params.date_to or "").strip() or None,
            date_basis=basis,
            channel_code=(params.channel_code or "").strip() or None,
            carrier_code=(params.carrier_code or "").strip() or None,
            customer=(params.customer or "").strip() or None,
            destination_port_code=(params.destination_port_code or "").strip() or None,
        )

    def _build_where(self, params: ShipmentPerformanceQuery) -> tuple[str, list[Any]]:
        conditions: list[str] = []
        values: list[Any] = []
        basis_col = DATE_BASIS_COLUMNS[params.date_basis]

        if params.date_from:
            conditions.append(f"date(substr({basis_col}, 1, 10)) >= date(?)")
            values.append(params.date_from[:10])
        if params.date_to:
            conditions.append(f"date(substr({basis_col}, 1, 10)) <= date(?)")
            values.append(params.date_to[:10])
        if params.channel_code:
            conditions.append("TRIM(channel_code) = ?")
            values.append(params.channel_code)
        if params.carrier_code:
            conditions.append("TRIM(carrier_code) = ?")
            values.append(params.carrier_code)
        if params.customer:
            conditions.append("(TRIM(customer) = ? OR TRIM(customer_no) = ?)")
            values.extend([params.customer, params.customer])
        if params.destination_port_code:
            conditions.append("TRIM(destination_port_code) = ?")
            values.append(params.destination_port_code)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return where, values

    def _fetch_rows(self, params: ShipmentPerformanceQuery) -> tuple[list[sqlite3.Row], bool]:
        where, values = self._build_where(params)
        sql = f"""
            SELECT
                id,
                shipment_no,
                customer,
                customer_no,
                channel_code,
                carrier_code,
                destination_port_code,
                etd,
                atd,
                eta,
                ata,
                expected_delivery_time,
                delivered_time,
                created_time
            FROM {TABLE_NAME}
            {where}
            ORDER BY datetime(COALESCE(atd, created_time)) DESC, shipment_no DESC
            LIMIT ?
        """
        with self._database.lock:
            rows = self._conn.execute(sql, [*values, MAX_ANALYSIS_ROWS + 1]).fetchall()
        truncated = len(rows) > MAX_ANALYSIS_ROWS
        if truncated:
            rows = rows[:MAX_ANALYSIS_ROWS]
        return rows, truncated

    def _enrich_row(self, row: sqlite3.Row) -> dict[str, Any]:
        signed = (row["delivered_time"] or "").strip() or None
        metrics = {
            "shipment_id": str(row["id"]),
            "shipment_no": str(row["shipment_no"] or ""),
            "customer": (row["customer"] or row["customer_no"] or "").strip() or None,
            "channel_code": (row["channel_code"] or "").strip() or None,
            "carrier_code": (row["carrier_code"] or "").strip() or None,
            "destination_port_code": (row["destination_port_code"] or "").strip() or None,
            "etd": (row["etd"] or "").strip() or None,
            "atd": (row["atd"] or "").strip() or None,
            "eta": (row["eta"] or "").strip() or None,
            "ata": (row["ata"] or "").strip() or None,
            "expected_delivery_time": (row["expected_delivery_time"] or "").strip() or None,
            "signed_time": signed,
            "departure_deviation_days": _day_diff(row["atd"], row["etd"]),
            "eta_deviation_days": _day_diff(row["ata"], row["eta"]),
            "sea_transit_days": _day_diff(row["ata"], row["atd"]),
            "post_arrival_days": _day_diff(row["delivered_time"], row["ata"]),
            "full_transit_days": _day_diff(row["delivered_time"], row["atd"]),
            "delivery_deviation_days": _day_diff(row["delivered_time"], row["expected_delivery_time"]),
        }
        metrics["anomaly_flags"] = _anomaly_flags(metrics)
        metrics["is_anomaly"] = bool(metrics["anomaly_flags"])
        return metrics

    def _aggregate_group(
        self,
        rows: list[dict[str, Any]],
        key_fn: Callable[[dict[str, Any]], str],
        label_fn: Callable[[dict[str, Any], str], str] | None = None,
    ) -> list[dict[str, Any]]:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = key_fn(row) or "(空)"
            buckets[key].append(row)

        out: list[dict[str, Any]] = []
        for key, items in buckets.items():
            total = len(items)
            signed = sum(1 for r in items if r.get("signed_time"))
            sea_vals = [float(r["sea_transit_days"]) for r in items if r.get("sea_transit_days") is not None]
            post_vals = [float(r["post_arrival_days"]) for r in items if r.get("post_arrival_days") is not None]
            full_vals = [float(r["full_transit_days"]) for r in items if r.get("full_transit_days") is not None]
            dev_vals = [
                float(r["delivery_deviation_days"])
                for r in items
                if r.get("delivery_deviation_days") is not None
            ]
            anomaly_count = sum(1 for r in items if r.get("is_anomaly"))
            computable = sum(
                1
                for r in items
                if r.get("full_transit_days") is not None or r.get("sea_transit_days") is not None
            )
            fastest_no, slowest_no, _, _ = _extreme_full_transit(items)
            label = label_fn(items[0], key) if label_fn else key
            out.append(
                {
                    "key": key,
                    "label": label,
                    "totalCount": total,
                    "signedCount": signed,
                    "signedRate": _ratio(signed, total),
                    "seaTransit": _metric_block(sea_vals),
                    "postArrival": _metric_block(post_vals),
                    "fullTransit": _metric_block(full_vals),
                    "deliveryDeviation": _metric_block(dev_vals),
                    "anomalyCount": anomaly_count,
                    "anomalyRate": _ratio(anomaly_count, computable or total),
                    "fastestShipmentNo": fastest_no,
                    "slowestShipmentNo": slowest_no,
                }
            )
        out.sort(key=lambda x: (-x["totalCount"], x["label"]))
        return out

    def _overview(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(rows)
        signed = sum(1 for r in rows if r.get("signed_time"))
        sea_vals = [float(r["sea_transit_days"]) for r in rows if r.get("sea_transit_days") is not None]
        post_vals = [float(r["post_arrival_days"]) for r in rows if r.get("post_arrival_days") is not None]
        full_vals = [float(r["full_transit_days"]) for r in rows if r.get("full_transit_days") is not None]
        dev_vals = [
            float(r["delivery_deviation_days"])
            for r in rows
            if r.get("delivery_deviation_days") is not None
        ]
        anomaly_count = sum(1 for r in rows if r.get("is_anomaly"))
        computable = sum(
            1
            for r in rows
            if r.get("full_transit_days") is not None or r.get("sea_transit_days") is not None
        )

        by_channel = self._aggregate_group(
            rows,
            lambda r: r.get("channel_code") or "(空)",
        )
        by_carrier = self._aggregate_group(
            rows,
            lambda r: r.get("carrier_code") or "(空)",
        )

        def rank_key(item: dict[str, Any]) -> tuple[float, int]:
            avg = item["fullTransit"].get("avgDays")
            sample = item["fullTransit"].get("sampleCount") or 0
            return (avg if avg is not None else -1.0, sample)

        channel_ranking = sorted(
            [x for x in by_channel if x["fullTransit"]["sampleCount"] > 0],
            key=rank_key,
            reverse=True,
        )[:10]
        carrier_ranking = sorted(
            [x for x in by_carrier if x["fullTransit"]["sampleCount"] > 0],
            key=rank_key,
            reverse=True,
        )[:10]

        fastest_no, slowest_no, min_full, max_full = _extreme_full_transit(rows)

        return {
            "totalCount": total,
            "signedCount": signed,
            "signedRate": _ratio(signed, total),
            "anomalyCount": anomaly_count,
            "anomalyRate": _ratio(anomaly_count, computable or total),
            "seaTransit": _metric_block(sea_vals),
            "postArrival": _metric_block(post_vals),
            "fullTransit": _metric_block(full_vals),
            "deliveryDeviation": _metric_block(dev_vals),
            "fastestSignedTransitDays": round(min_full, 1) if min_full is not None else None,
            "fastestSignedShipmentNo": fastest_no,
            "slowestSignedTransitDays": round(max_full, 1) if max_full is not None else None,
            "slowestSignedShipmentNo": slowest_no,
            "channelRanking": channel_ranking,
            "carrierRanking": carrier_ranking,
        }

    def _by_carrier_channel(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            carrier = row.get("carrier_code") or "(空)"
            channel = row.get("channel_code") or "(空)"
            buckets[(carrier, channel)].append(row)

        out: list[dict[str, Any]] = []
        for (carrier, channel), items in buckets.items():
            total = len(items)
            signed = sum(1 for r in items if r.get("signed_time"))
            sea_vals = [float(r["sea_transit_days"]) for r in items if r.get("sea_transit_days") is not None]
            full_vals = [float(r["full_transit_days"]) for r in items if r.get("full_transit_days") is not None]
            anomaly_count = sum(1 for r in items if r.get("is_anomaly"))
            computable = sum(1 for r in items if r.get("full_transit_days") is not None)
            out.append(
                {
                    "carrierCode": carrier,
                    "channelCode": channel,
                    "totalCount": total,
                    "signedCount": signed,
                    "seaTransit": _metric_block(sea_vals),
                    "fullTransit": _metric_block(full_vals),
                    "anomalyCount": anomaly_count,
                    "anomalyRate": _ratio(anomaly_count, computable or total),
                }
            )
        out.sort(key=lambda x: (-x["totalCount"], x["carrierCode"], x["channelCode"]))
        return out

    def analyze(self, params: ShipmentPerformanceQuery) -> dict[str, Any]:
        query = self._normalize_query(params)
        raw_rows, truncated = self._fetch_rows(query)
        rows = [self._enrich_row(r) for r in raw_rows]
        return {
            "filters": query.model_dump(by_alias=True),
            "truncated": truncated,
            "analyzedCount": len(rows),
            "overview": self._overview(rows),
            "byChannel": self._aggregate_group(rows, lambda r: r.get("channel_code") or "(空)"),
            "byCarrier": self._aggregate_group(rows, lambda r: r.get("carrier_code") or "(空)"),
            "byCarrierChannel": self._by_carrier_channel(rows),
            "byCustomer": self._aggregate_group(
                rows,
                lambda r: r.get("customer") or "(空)",
                lambda item, key: item.get("customer") or key,
            ),
        }

    def _load_enriched_rows(self, params: ShipmentPerformanceQuery) -> tuple[list[dict[str, Any]], bool]:
        query = self._normalize_query(params)
        raw_rows, truncated = self._fetch_rows(query)
        return [self._enrich_row(r) for r in raw_rows], truncated

    def details(
        self,
        params: ShipmentPerformanceQuery,
        *,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "fullTransitDays",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        page = max(1, page)
        page_size = max(1, min(page_size, 200))
        rows, truncated = self._load_enriched_rows(params)
        field = SORTABLE_DETAIL_FIELDS.get(sort_by, "full_transit_days")
        reverse = (sort_order or "desc").lower() != "asc"

        def sort_val(row: dict[str, Any]) -> tuple:
            val = row.get(field)
            if val is None:
                return (1, "")
            if isinstance(val, (int, float)):
                return (0, val)
            return (0, str(val))

        rows.sort(key=sort_val, reverse=reverse)
        total = len(rows)
        start = (page - 1) * page_size
        page_rows = rows[start : start + page_size]
        items = [
            {
                "shipmentId": r["shipment_id"],
                "shipmentNo": r["shipment_no"],
                "customer": r.get("customer"),
                "channelCode": r.get("channel_code"),
                "carrierCode": r.get("carrier_code"),
                "destinationPortCode": r.get("destination_port_code"),
                "etd": r.get("etd"),
                "atd": r.get("atd"),
                "eta": r.get("eta"),
                "ata": r.get("ata"),
                "expectedDeliveryTime": r.get("expected_delivery_time"),
                "signedTime": r.get("signed_time"),
                "departureDeviationDays": r.get("departure_deviation_days"),
                "etaDeviationDays": r.get("eta_deviation_days"),
                "seaTransitDays": r.get("sea_transit_days"),
                "postArrivalDays": r.get("post_arrival_days"),
                "fullTransitDays": r.get("full_transit_days"),
                "deliveryDeviationDays": r.get("delivery_deviation_days"),
                "anomalyFlags": r.get("anomaly_flags") or [],
            }
            for r in page_rows
        ]
        return {
            "items": items,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "truncated": truncated,
        }

    def export_csv(self, params: ShipmentPerformanceQuery) -> tuple[str, bool]:
        rows, truncated = self._load_enriched_rows(params)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "运单号",
                "客户",
                "渠道",
                "承运商",
                "目的港",
                "ETD",
                "ATD",
                "ETA",
                "ATA",
                "预计送仓",
                "签收时间",
                "开船偏差(天)",
                "ETA偏差(天)",
                "海运时效(天)",
                "到港后送仓(天)",
                "全程时效(天)",
                "预计送仓偏差(天)",
                "异常标记",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.get("shipment_no") or "",
                    r.get("customer") or "",
                    r.get("channel_code") or "",
                    r.get("carrier_code") or "",
                    r.get("destination_port_code") or "",
                    r.get("etd") or "",
                    r.get("atd") or "",
                    r.get("eta") or "",
                    r.get("ata") or "",
                    r.get("expected_delivery_time") or "",
                    r.get("signed_time") or "",
                    r.get("departure_deviation_days") if r.get("departure_deviation_days") is not None else "",
                    r.get("eta_deviation_days") if r.get("eta_deviation_days") is not None else "",
                    r.get("sea_transit_days") if r.get("sea_transit_days") is not None else "",
                    r.get("post_arrival_days") if r.get("post_arrival_days") is not None else "",
                    r.get("full_transit_days") if r.get("full_transit_days") is not None else "",
                    r.get("delivery_deviation_days") if r.get("delivery_deviation_days") is not None else "",
                    "；".join(r.get("anomaly_flags") or []),
                ]
            )
        return buf.getvalue(), truncated
