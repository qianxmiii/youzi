"""运单 shipments 表 CRUD。"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from .connection import Database
from ..internal_tracking import INTERNAL_WAREHOUSE_PLACEHOLDER, mask_internal_summary
from .datetime_util import now_str
from .carrier_tracking_logs_table import TABLE_NAME as CARRIER_TRACKING_TABLE
from .internal_tracking_logs_table import TABLE_NAME as INTERNAL_TRACKING_TABLE
from .shipments_table import TABLE_NAME
from .channels_repository import TABLE_NAME as CHANNEL_CODES_TABLE
from .exception_duration import duration_seconds, format_duration
from .tracking_freshness import (
    carrier_ahead_of_internal_sql,
    carrier_freshness_sql,
    freshness_stats_sql,
    internal_freshness_sql,
    validate_freshness,
)

_LIST_FROM = (
    f"{TABLE_NAME} s LEFT JOIN {CHANNEL_CODES_TABLE} cc ON s.channel_code = cc.code"
)
_LIST_SELECT = "s.*, cc.name_zh AS _channel_name_zh, cc.category AS _channel_category"

# 轨迹同步：仅转运中；已签收(DELIVERED)、查验等不参与拉取
_TRACKING_SYNC_ELIGIBLE_SQL = "status_code = 'IN_TRANSIT'"

# 可写字段（不含 id / shipment_no / created_time）
_UPDATABLE = (
    "customer",
    "customer_no",
    "channel_code",
    "country_code",
    "address_type",
    "address_code",
    "delivery_address",
    "ctns",
    "zipcode",
    "product_name",
    "origin_warehouse_code",
    "supplier_name",
    "carrier_code",
    "customer_shipment_id",
    "amazon_ref_id",
    "vessel_name",
    "voyage_no",
    "vessel_voyage",
    "etd",
    "eta",
    "atd",
    "ata",
    "origin_port_code",
    "destination_port_code",
    "delivered_time",
    "status_code",
)


def _exception_duration_seconds(row: sqlite3.Row) -> int | None:
    code = (row["exception_code"] or "").strip()
    opened = (row["exception_opened_time"] or "").strip()
    if not code or not opened:
        return None
    return duration_seconds(opened, None)


def _exception_duration_label(row: sqlite3.Row) -> str | None:
    secs = _exception_duration_seconds(row)
    if secs is None:
        return None
    return format_duration(secs)


def _row_to_api(row: sqlite3.Row) -> dict[str, Any]:
    latest_time, latest_desc = mask_internal_summary(
        row["latest_tracking_time"], row["latest_tracking_desc"]
    )
    return {
        "id": row["id"],
        "shipmentNo": row["shipment_no"],
        "customer": row["customer"],
        "customerNo": row["customer_no"],
        "channelCode": row["channel_code"],
        "channelNameZh": (
            (row["_channel_name_zh"] or "").strip()
            if "_channel_name_zh" in row.keys()
            else ""
        )
        or None,
        "channelCategory": (
            (row["_channel_category"] or "").strip()
            if "_channel_category" in row.keys()
            else ""
        )
        or None,
        "countryCode": row["country_code"],
        "addressType": row["address_type"],
        "addressCode": row["address_code"],
        "deliveryAddress": row["delivery_address"],
        "ctns": row["ctns"],
        "zipcode": row["zipcode"],
        "productName": row["product_name"],
        "originWarehouseCode": row["origin_warehouse_code"],
        "supplierName": row["supplier_name"],
        "carrierCode": row["carrier_code"],
        "carrierId": row["carrier_id"],
        "trackingNumber": row["tracking_number"],
        "customerShipmentId": row["customer_shipment_id"],
        "amazonRefId": row["amazon_ref_id"],
        "vesselName": row["vessel_name"],
        "voyageNo": row["voyage_no"],
        "vesselVoyage": row["vessel_voyage"],
        "etd": row["etd"],
        "eta": row["eta"],
        "atd": row["atd"],
        "ata": row["ata"],
        "originPortCode": row["origin_port_code"],
        "destinationPortCode": row["destination_port_code"],
        "deliveredTime": row["delivered_time"],
        "statusCode": row["status_code"],
        "exceptionCode": row["exception_code"],
        "exceptionOpenedTime": row["exception_opened_time"],
        "exceptionDurationSeconds": _exception_duration_seconds(row),
        "exceptionDurationLabel": _exception_duration_label(row),
        "latestTrackingTime": latest_time,
        "latestTrackingDesc": latest_desc,
        "trackingLogCount": row["tracking_log_count"],
        "latestCarrierTime": row["latest_carrier_time"],
        "latestCarrierDesc": row["latest_carrier_desc"],
        "carrierLogCount": row["carrier_log_count"],
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    snake_map = {
        "shipmentNo": "shipment_no",
        "customerNo": "customer_no",
        "channelCode": "channel_code",
        "countryCode": "country_code",
        "addressType": "address_type",
        "addressCode": "address_code",
        "deliveryAddress": "delivery_address",
        "ctns": "ctns",
        "productName": "product_name",
        "originWarehouseCode": "origin_warehouse_code",
        "supplierName": "supplier_name",
        "carrierCode": "carrier_code",
        "carrierId": "carrier_id",
        "trackingNumber": "tracking_number",
        "customerShipmentId": "customer_shipment_id",
        "amazonRefId": "amazon_ref_id",
        "vesselName": "vessel_name",
        "voyageNo": "voyage_no",
        "vesselVoyage": "vessel_voyage",
        "originPortCode": "origin_port_code",
        "destinationPortCode": "destination_port_code",
        "deliveredTime": "delivered_time",
        "statusCode": "status_code",
        "createdTime": "created_time",
        "updatedTime": "updated_time",
    }
    for key, value in data.items():
        col = snake_map.get(key, key)
        if col in _UPDATABLE or col == "shipment_no":
            out[col] = value
    return out


class ShipmentsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def list_rows(
        self,
        *,
        search: str | None = None,
        tracking_search: str | None = None,
        shipment_nos: list[str] | None = None,
        status_code: str | None = None,
        exception_code: str | None = None,
        has_exception: bool | None = None,
        customer: str | None = None,
        carrier_code: str | None = None,
        country_code: str | None = None,
        channel_code: str | None = None,
        channel_name_zh: str | None = None,
        channel_category: str | None = None,
        internal_freshness: str | None = None,
        carrier_freshness: str | None = None,
        carrier_ahead_of_internal: bool | None = None,
        min_stale_days: int | None = None,
        no_tracking: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        conditions: list[str] = []
        params: list[Any] = []
        cleaned_nos = list(
            dict.fromkeys(s.strip() for s in (shipment_nos or []) if s and s.strip())
        )
        if cleaned_nos:
            if len(cleaned_nos) == 1:
                q = f"%{cleaned_nos[0]}%"
                conditions.append("(s.shipment_no LIKE ? OR s.customer_no LIKE ?)")
                params.extend([q, q])
            else:
                placeholders = ", ".join("?" * len(cleaned_nos))
                conditions.append(
                    f"(s.shipment_no IN ({placeholders}) OR s.customer_no IN ({placeholders}))"
                )
                params.extend(cleaned_nos + cleaned_nos)
        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append(
                "(s.customer LIKE ? OR s.customer_no LIKE ? "
                "OR s.address_code LIKE ? OR s.delivery_address LIKE ?)"
            )
            params.extend([q, q, q, q])
        if tracking_search and tracking_search.strip():
            tq = f"%{tracking_search.strip()}%"
            conditions.append(
                f"""
                (
                  s.shipment_no IN (
                    SELECT shipment_no FROM {INTERNAL_TRACKING_TABLE}
                    WHERE tracking_desc LIKE ?
                    UNION
                    SELECT shipment_no FROM {CARRIER_TRACKING_TABLE}
                    WHERE tracking_desc LIKE ?
                  )
                  OR s.latest_tracking_desc LIKE ?
                  OR s.latest_carrier_desc LIKE ?
                )
                """
            )
            params.extend([tq, tq, tq, tq])
        if status_code and status_code.strip():
            conditions.append("s.status_code = ?")
            params.append(status_code.strip())
        if exception_code and exception_code.strip():
            conditions.append("s.exception_code = ?")
            params.append(exception_code.strip())
        if has_exception is True:
            conditions.append(
                "s.exception_code IS NOT NULL AND TRIM(s.exception_code) != ''"
            )
        elif has_exception is False:
            conditions.append(
                "(s.exception_code IS NULL OR TRIM(s.exception_code) = '')"
            )
        if customer and customer.strip():
            conditions.append("s.customer = ?")
            params.append(customer.strip())
        if carrier_code and carrier_code.strip():
            conditions.append("s.carrier_code = ?")
            params.append(carrier_code.strip())
        if country_code and country_code.strip():
            conditions.append("s.country_code = ?")
            params.append(country_code.strip())
        if channel_code and channel_code.strip():
            conditions.append("s.channel_code = ?")
            params.append(channel_code.strip())
        if channel_name_zh and channel_name_zh.strip():
            conditions.append("cc.name_zh = ?")
            params.append(channel_name_zh.strip())
        if channel_category and channel_category.strip():
            conditions.append("cc.category = ?")
            params.append(channel_category.strip())
        if internal_freshness:
            frag, frag_params = internal_freshness_sql(
                validate_freshness(internal_freshness) or ""
            )
            conditions.append(frag)
            params.extend(frag_params)
        if carrier_freshness:
            frag, frag_params = carrier_freshness_sql(
                validate_freshness(carrier_freshness) or ""
            )
            conditions.append(frag)
            params.extend(frag_params)
        if carrier_ahead_of_internal is True:
            frag, frag_params = carrier_ahead_of_internal_sql("s")
            conditions.append(frag)
            params.extend(frag_params)
        if no_tracking:
            conditions.append(
                f"(s.latest_tracking_time IS NULL OR TRIM(s.latest_tracking_time) = '' "
                f"OR TRIM(s.latest_tracking_desc) = ?)"
            )
            params.append(INTERNAL_WAREHOUSE_PLACEHOLDER)
        elif min_stale_days is not None and min_stale_days > 0:
            conditions.append(
                """
                s.latest_tracking_time IS NOT NULL AND TRIM(s.latest_tracking_time) != ''
                AND datetime(s.latest_tracking_time) <= datetime('now', ?)
                """
            )
            params.append(f"-{int(min_stale_days)} days")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {_LIST_FROM} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT {_LIST_SELECT} FROM {_LIST_FROM} {where}
                ORDER BY datetime(s.latest_tracking_time) DESC,
                         datetime(s.updated_time) DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return {
            "items": [_row_to_api(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def tracking_freshness_stats(self) -> dict[str, Any]:
        sql, params = freshness_stats_sql()
        with self._database.lock:
            row = self._conn.execute(sql, params).fetchone()
        return {
            "internal": {
                "today": int(row["internal_today"] or 0),
                "within3d": int(row["internal_within3d"] or 0),
                "older": int(row["internal_older"] or 0),
                "none": int(row["internal_none"] or 0),
            },
            "carrier": {
                "today": int(row["carrier_today"] or 0),
                "within3d": int(row["carrier_within3d"] or 0),
                "older": int(row["carrier_older"] or 0),
                "none": int(row["carrier_none"] or 0),
            },
            "carrierAheadOfInternal": int(row["carrier_ahead_of_internal"] or 0),
        }

    def list_filter_options(self) -> dict[str, Any]:
        """运单表中去重后的筛选选项。"""
        cols = ("customer", "carrier_code", "country_code", "channel_code", "status_code")
        out: dict[str, list[str]] = {}
        with self._database.lock:
            for col in cols:
                rows = self._conn.execute(
                    f"""
                    SELECT DISTINCT {col} AS v FROM {TABLE_NAME}
                    WHERE {col} IS NOT NULL AND TRIM({col}) != ''
                    ORDER BY {col}
                    """
                ).fetchall()
                out[col] = [str(r["v"]) for r in rows]
            exc_in_use = self._conn.execute(
                f"""
                SELECT DISTINCT exception_code AS v FROM {TABLE_NAME}
                WHERE exception_code IS NOT NULL AND TRIM(exception_code) != ''
                ORDER BY exception_code
                """
            ).fetchall()
            exception_defs = self._conn.execute(
                """
                SELECT code, name_zh FROM shipment_exception_codes
                WHERE is_active = 1
                ORDER BY sort_order, code
                """
            ).fetchall()
            channel_name_rows = self._conn.execute(
                f"""
                SELECT DISTINCT cc.name_zh AS v
                FROM {TABLE_NAME} s
                INNER JOIN {CHANNEL_CODES_TABLE} cc ON s.channel_code = cc.code
                WHERE cc.name_zh IS NOT NULL AND TRIM(cc.name_zh) != ''
                ORDER BY cc.name_zh
                """
            ).fetchall()
            channel_category_rows = self._conn.execute(
                f"""
                SELECT DISTINCT cc.category AS v
                FROM {TABLE_NAME} s
                INNER JOIN {CHANNEL_CODES_TABLE} cc ON s.channel_code = cc.code
                WHERE cc.category IS NOT NULL AND TRIM(cc.category) != ''
                ORDER BY cc.category
                """
            ).fetchall()
        return {
            "customers": out["customer"],
            "carrierCodes": out["carrier_code"],
            "countryCodes": out["country_code"],
            "channelCodes": out["channel_code"],
            "channelNameZhs": [str(r["v"]) for r in channel_name_rows],
            "channelCategories": [str(r["v"]) for r in channel_category_rows],
            "statusCodes": out["status_code"],
            "exceptionCodes": [str(r["v"]) for r in exc_in_use],
            "exceptionTypes": [
                {"code": str(r["code"]), "nameZh": str(r["name_zh"] or r["code"])}
                for r in exception_defs
            ],
        }

    def update_internal_tracking_summary(
        self,
        shipment_no: str,
        latest_time: str,
        latest_desc: str,
        *,
        log_count: int | None = None,
        status_code: str | None = None,
        delivered_time: str | None = None,
    ) -> None:
        sn = shipment_no.strip()
        count = log_count
        with self._database.lock:
            if count is None:
                count = self._conn.execute(
                    "SELECT COUNT(*) AS c FROM internal_tracking_logs WHERE shipment_no = ?",
                    (sn,),
                ).fetchone()["c"]
            sets = [
                "latest_tracking_time = ?",
                "latest_tracking_desc = ?",
                "tracking_log_count = ?",
                "updated_time = ?",
            ]
            params: list[Any] = [
                latest_time,
                latest_desc or "",
                int(count),
                now_str(),
            ]
            sc = (status_code or "").strip()
            if sc:
                sets.append("status_code = ?")
                params.append(sc)
            dt = (delivered_time or "").strip()
            if dt:
                sets.append("delivered_time = ?")
                params.append(dt)
            params.append(sn)
            self._conn.execute(
                f"UPDATE {TABLE_NAME} SET {', '.join(sets)} WHERE shipment_no = ?",
                params,
            )
            self._conn.commit()

    def update_tracking_summary(
        self,
        shipment_no: str,
        latest_time: str,
        latest_desc: str,
        *,
        log_count: int | None = None,
    ) -> None:
        """兼容别名：内部轨迹摘要。"""
        self.update_internal_tracking_summary(
            shipment_no, latest_time, latest_desc, log_count=log_count
        )

    def set_carrier_id_if_empty(self, shipment_no: str, carrier_id: str) -> bool:
        """承运商侧单号/工作号：仅当库内为空时写入，返回是否新写入。"""
        sn = shipment_no.strip()
        cid = (carrier_id or "").strip()
        if not sn or not cid:
            return False
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET carrier_id = ?
                WHERE shipment_no = ?
                  AND (carrier_id IS NULL OR TRIM(carrier_id) = '')
                """,
                (cid, sn),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def set_tracking_number_if_empty(self, shipment_no: str, tracking_number: str) -> bool:
        """尾程快递单号（UPS/FedEx 等）：仅当库内为空时写入。"""
        sn = shipment_no.strip()
        tn = (tracking_number or "").strip()
        if not sn or not tn:
            return False
        with self._database.lock:
            cur = self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET tracking_number = ?
                WHERE shipment_no = ?
                  AND (tracking_number IS NULL OR TRIM(tracking_number) = '')
                """,
                (tn, sn),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def update_carrier_tracking_summary(
        self,
        shipment_no: str,
        latest_time: str,
        latest_desc: str,
        *,
        log_count: int | None = None,
        carrier_id: str | None = None,
        tracking_number: str | None = None,
    ) -> None:
        sn = shipment_no.strip()
        count = log_count
        with self._database.lock:
            if count is None:
                count = self._conn.execute(
                    "SELECT COUNT(*) AS c FROM carrier_tracking_logs WHERE shipment_no = ?",
                    (sn,),
                ).fetchone()["c"]
            self._conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET latest_carrier_time = ?,
                    latest_carrier_desc = ?,
                    carrier_log_count = ?
                WHERE shipment_no = ?
                """,
                (latest_time, latest_desc or "", int(count), sn),
            )
            cid = (carrier_id or "").strip()
            if cid:
                self._conn.execute(
                    f"""
                    UPDATE {TABLE_NAME}
                    SET carrier_id = ?
                    WHERE shipment_no = ?
                      AND (carrier_id IS NULL OR TRIM(carrier_id) = '')
                    """,
                    (cid, sn),
                )
            tn = (tracking_number or "").strip()
            if tn:
                self._conn.execute(
                    f"""
                    UPDATE {TABLE_NAME}
                    SET tracking_number = ?
                    WHERE shipment_no = ?
                      AND (tracking_number IS NULL OR TRIM(tracking_number) = '')
                    """,
                    (tn, sn),
                )
            self._conn.commit()

    def list_for_carrier_sync(
        self,
        shipment_nos: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """承运商轨迹同步：仅 status_code=IN_TRANSIT（含全库与指定运单号）。"""
        with self._database.lock:
            if shipment_nos:
                cleaned = list(dict.fromkeys(s.strip() for s in shipment_nos if s and s.strip()))
                if not cleaned:
                    return []
                placeholders = ", ".join("?" * len(cleaned))
                rows = self._conn.execute(
                    f"""
                    SELECT shipment_no, customer, carrier_code, supplier_name, carrier_id,
                           tracking_number, latest_carrier_time, latest_carrier_desc
                    FROM {TABLE_NAME}
                    WHERE TRIM(shipment_no) != ''
                      AND {_TRACKING_SYNC_ELIGIBLE_SQL}
                      AND shipment_no IN ({placeholders})
                    ORDER BY shipment_no
                    """,
                    cleaned,
                ).fetchall()
            else:
                rows = self._conn.execute(
                    f"""
                    SELECT shipment_no, customer, carrier_code, supplier_name, carrier_id,
                           tracking_number, latest_carrier_time, latest_carrier_desc
                    FROM {TABLE_NAME}
                    WHERE TRIM(shipment_no) != ''
                      AND {_TRACKING_SYNC_ELIGIBLE_SQL}
                    ORDER BY shipment_no
                    """
                ).fetchall()
        return [
            {
                "shipment_no": r["shipment_no"],
                "customer": r["customer"] or "",
                "carrier_code": r["carrier_code"] or "",
                "supplier_name": r["supplier_name"] or "",
                "carrier_id": r["carrier_id"] or "",
                "tracking_number": r["tracking_number"] or "",
                "latest_carrier_time": r["latest_carrier_time"] or "",
                "latest_carrier_desc": r["latest_carrier_desc"] or "",
            }
            for r in rows
        ]

    def get_by_id(self, item_id: str) -> dict[str, Any] | None:
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE id = ?",
                (item_id,),
            ).fetchone()
        return _row_to_api(row) if row else None

    def get_by_shipment_no(self, shipment_no: str) -> dict[str, Any] | None:
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE shipment_no = ?",
                (shipment_no.strip(),),
            ).fetchone()
        return _row_to_api(row) if row else None

    def get_by_shipment_or_customer_no(self, no: str) -> dict[str, Any] | None:
        """运单号精确匹配；否则按客户订单号匹配首条。"""
        key = no.strip()
        if not key:
            return None
        row = self.get_by_shipment_no(key)
        if row:
            return row
        with self._database.lock:
            found = self._conn.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE customer_no = ?
                ORDER BY datetime(updated_time) DESC
                LIMIT 1
                """,
                (key,),
            ).fetchone()
        return _row_to_api(found) if found else None

    def list_for_tracking_sync(
        self,
        shipment_nos: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """内部轨迹同步：仅 status_code=IN_TRANSIT（含全库与指定运单号）。"""
        with self._database.lock:
            if shipment_nos:
                cleaned = list(dict.fromkeys(s.strip() for s in shipment_nos if s and s.strip()))
                if not cleaned:
                    return []
                placeholders = ", ".join("?" * len(cleaned))
                rows = self._conn.execute(
                    f"""
                    SELECT shipment_no, customer, channel_code, carrier_code,
                           status_code, latest_tracking_time, latest_tracking_desc
                    FROM {TABLE_NAME}
                    WHERE TRIM(shipment_no) != ''
                      AND {_TRACKING_SYNC_ELIGIBLE_SQL}
                      AND shipment_no IN ({placeholders})
                    ORDER BY shipment_no
                    """,
                    cleaned,
                ).fetchall()
            else:
                rows = self._conn.execute(
                    f"""
                    SELECT shipment_no, customer, channel_code, carrier_code,
                           status_code, latest_tracking_time, latest_tracking_desc
                    FROM {TABLE_NAME}
                    WHERE TRIM(shipment_no) != ''
                      AND {_TRACKING_SYNC_ELIGIBLE_SQL}
                    ORDER BY shipment_no
                    """
                ).fetchall()
        return [
            {
                "tracking_number": r["shipment_no"],
                "customer": r["customer"] or "",
                "channel": r["channel_code"] or "",
                "carrier": r["carrier_code"] or "",
                "status_code": r["status_code"] or "",
                "latest_tracking_time": r["latest_tracking_time"] or "",
                "latest_tracking_desc": r["latest_tracking_desc"] or "",
            }
            for r in rows
        ]

    def insert_row(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = _normalize_payload(data)
        shipment_no = (payload.get("shipment_no") or "").strip()
        if not shipment_no:
            raise ValueError("运单号不能为空")
        now = now_str()
        rid = str(uuid.uuid4())
        cols = ["id", "shipment_no", "created_time", "updated_time"]
        vals: list[Any] = [rid, shipment_no, now, now]
        for col in _UPDATABLE:
            if col in payload:
                cols.append(col)
                vals.append(payload[col])
        placeholders = ", ".join("?" for _ in cols)
        col_sql = ", ".join(cols)
        with self._database.lock:
            self._conn.execute(
                f"INSERT INTO {TABLE_NAME} ({col_sql}) VALUES ({placeholders})",
                vals,
            )
            self._conn.commit()
        row = self.get_by_id(rid)
        if row is None:
            raise RuntimeError("插入后读取失败")
        return row

    def update_row(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = _normalize_payload(data)
        payload.pop("shipment_no", None)
        if not payload:
            existing = self.get_by_id(item_id)
            if existing is None:
                raise KeyError(item_id)
            return existing
        sets = [f"{col} = ?" for col in payload]
        sets.append("updated_time = ?")
        vals = list(payload.values()) + [now_str(), item_id]
        with self._database.lock:
            cur = self._conn.execute(
                f"UPDATE {TABLE_NAME} SET {', '.join(sets)} WHERE id = ?",
                vals,
            )
            self._conn.commit()
            if cur.rowcount == 0:
                raise KeyError(item_id)
        row = self.get_by_id(item_id)
        if row is None:
            raise KeyError(item_id)
        return row

    def upsert_by_shipment_no(self, data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """返回 (记录, 是否新建)。"""
        payload = _normalize_payload(data)
        shipment_no = (payload.get("shipment_no") or "").strip()
        if not shipment_no:
            raise ValueError("运单号不能为空")
        existing = self.get_by_shipment_no(shipment_no)
        if existing is None:
            if not payload.get("status_code"):
                payload["status_code"] = "UNKNOWN"
            return self.insert_row(payload), True
        # 更新：仅覆盖 Excel 中填写的字段，空单元格不写入
        update_payload = {
            k: v for k, v in payload.items() if k != "shipment_no" and v is not None
        }
        if not update_payload:
            return existing, False
        return self.update_row(existing["id"], update_payload), False

    def delete_row(self, item_id: str) -> bool:
        with self._database.lock:
            cur = self._conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE id = ?",
                (item_id,),
            )
            self._conn.commit()
            return cur.rowcount > 0
