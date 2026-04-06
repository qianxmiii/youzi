"""
报价历史表：列与 index.html / logistics.js 的 quoteData 一致（库内蛇形，API 驼峰）。

客户代码 customer、品名 product_name 与「派送地址代码 address、国家 country」分栏存储，
便于按客户/品名统计；历史上曾把整份报价塞进 extra_json 一段 JSON，不利于 SQL 查询与字段演进，已弃用。
旧表（customer/channel/extra_json）会迁到新结构后删除备份表。
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from . import app_settings_table
from .connection import Database

TABLE_NAME = "quote_history"
LEGACY_NAME = "quote_history_legacy"


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE_NAME,),
    )
    if cur.fetchone() is None:
        _create_fresh_table(conn)
        return
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
    if "address" in cols:
        _ensure_quote_history_incremental_columns(conn)
        return
    conn.execute(f"ALTER TABLE {TABLE_NAME} RENAME TO {LEGACY_NAME}")
    _create_fresh_table(conn)
    try:
        _migrate_legacy_rows_loose(conn)
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {LEGACY_NAME}")


def _ensure_quote_history_incremental_columns(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
    if "customer" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN customer TEXT NOT NULL DEFAULT '00'"
        )
    if "product_name" not in cols:
        conn.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN product_name TEXT NOT NULL DEFAULT '00'"
        )


def _row_as_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _migrate_legacy_rows_loose(conn: sqlite3.Connection) -> None:
    leg_cols = {r[1] for r in conn.execute(f"PRAGMA table_info({LEGACY_NAME})").fetchall()}
    for row in conn.execute(f"SELECT * FROM {LEGACY_NAME}").fetchall():
        rd = _row_as_dict(row)
        if "extra_json" in leg_cols and rd.get("extra_json"):
            try:
                ex = json.loads(rd["extra_json"] or "{}")
            except Exception:
                ex = {}
            if isinstance(ex, dict) and ex.get("address") is not None:
                _insert_full_row_from_payload(
                    conn,
                    ex,
                    str(rd["id"]),
                    str(rd["created_at"]),
                    str(rd["updated_at"]),
                    source=str(ex.get("_source") or "index"),
                )
                continue
        _insert_full_row_from_payload(
            conn,
            {
                "timestamp": str(rd.get("updated_at") or rd.get("created_at") or ""),
                "address": str(rd.get("customer") or ""),
                "deliveryMethod": str(rd.get("channel") or ""),
                "notes": str(rd.get("note") or ""),
                "totalPriceUsd": float(rd.get("amount") or 0),
                "quoteType": "通用",
            },
            str(rd["id"]),
            str(rd["created_at"]),
            str(rd["updated_at"]),
            source="admin_legacy",
        )


def _create_fresh_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE {TABLE_NAME} (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'index',
            customer TEXT NOT NULL DEFAULT '00',
            product_name TEXT NOT NULL DEFAULT '00',
            timestamp TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            postcode TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT '',
            delivery_method TEXT NOT NULL DEFAULT '',
            origin TEXT NOT NULL DEFAULT '',
            quantity REAL NOT NULL DEFAULT 0,
            weight REAL NOT NULL DEFAULT 0,
            volume REAL NOT NULL DEFAULT 0,
            cost_rmb REAL NOT NULL DEFAULT 0,
            profit_rmb REAL NOT NULL DEFAULT 0,
            price_rmb REAL NOT NULL DEFAULT 0,
            price_usd REAL NOT NULL DEFAULT 0,
            is_remote INTEGER NOT NULL DEFAULT 0,
            has_residential INTEGER NOT NULL DEFAULT 0,
            has_battery INTEGER NOT NULL DEFAULT 0,
            is_oversize INTEGER NOT NULL DEFAULT 0,
            oversize_fee REAL NOT NULL DEFAULT 0,
            oversize_quantity REAL NOT NULL DEFAULT 0,
            is_overweight INTEGER NOT NULL DEFAULT 0,
            overweight_fee REAL NOT NULL DEFAULT 0,
            overweight_quantity REAL NOT NULL DEFAULT 0,
            is_moq INTEGER NOT NULL DEFAULT 0,
            moq_value REAL NOT NULL DEFAULT 0,
            has_pickup_fee INTEGER NOT NULL DEFAULT 0,
            pickup_fee_rmb REAL NOT NULL DEFAULT 0,
            pickup_fee_usd REAL NOT NULL DEFAULT 0,
            is_ddu INTEGER NOT NULL DEFAULT 0,
            is_usd INTEGER NOT NULL DEFAULT 0,
            charge_weight REAL NOT NULL DEFAULT 0,
            charge_cbm REAL NOT NULL DEFAULT 0,
            volume_ratio REAL NOT NULL DEFAULT 0,
            total_price_usd REAL NOT NULL DEFAULT 0,
            total_price_rmb REAL NOT NULL DEFAULT 0,
            unit_price_rmb REAL NOT NULL DEFAULT 0,
            quote_type TEXT NOT NULL DEFAULT '通用',
            notes TEXT NOT NULL DEFAULT ''
        )
        """
    )


def _bool_int(v: Any) -> int:
    return 1 if v else 0


def _float_val(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _payload_to_row_tuple(
    payload: dict[str, Any],
    record_id: str,
    created_at: str,
    updated_at: str,
    source: str,
) -> tuple[Any, ...]:
    def _txt(key: str, alt: tuple[str, ...] = (), default: str = "") -> str:
        for k in (key, *alt):
            if k in payload and payload[k] is not None:
                return str(payload[k])
        return default

    return (
        record_id,
        created_at,
        updated_at,
        source,
        _txt("customer", default="00")[:500] or "00",
        _txt("productName", ("product_name",), "00")[:500] or "00",
        str(payload.get("timestamp") or ""),
        str(payload.get("address") or ""),
        str(payload.get("postcode") or ""),
        str(payload.get("country") or ""),
        str(payload.get("deliveryMethod") or ""),
        str(payload.get("origin") or ""),
        _float_val(payload.get("quantity")),
        _float_val(payload.get("weight")),
        _float_val(payload.get("volume")),
        _float_val(payload.get("costRmb")),
        _float_val(payload.get("profitRmb")),
        _float_val(payload.get("priceRmb")),
        _float_val(payload.get("priceUsd")),
        _bool_int(payload.get("isRemote")),
        _bool_int(payload.get("hasResidential")),
        _bool_int(payload.get("hasBattery")),
        _bool_int(payload.get("isOversize")),
        _float_val(payload.get("oversizeFee")),
        _float_val(payload.get("oversizeQuantity")),
        _bool_int(payload.get("isOverweight")),
        _float_val(payload.get("overweightFee")),
        _float_val(payload.get("overweightQuantity")),
        _bool_int(payload.get("isMOQ")),
        _float_val(payload.get("moqValue")),
        _bool_int(payload.get("hasPickupFee")),
        _float_val(payload.get("pickupFeeRmb")),
        _float_val(payload.get("pickupFeeUsd")),
        _bool_int(payload.get("isDDU")),
        _bool_int(payload.get("isUSD")),
        _float_val(payload.get("chargeWeight")),
        _float_val(payload.get("chargeCBM")),
        _float_val(payload.get("volumeRatio")),
        _float_val(payload.get("totalPriceUsd")),
        _float_val(payload.get("totalPriceRmb")),
        _float_val(payload.get("unitPriceRmb")),
        str(payload.get("quoteType") or "通用"),
        str(payload.get("notes") or ""),
    )


_INSERT_SQL = f"""
INSERT OR REPLACE INTO {TABLE_NAME} (
    id, created_at, updated_at, source,
    customer, product_name,
    timestamp, address, postcode, country, delivery_method, origin,
    quantity, weight, volume,
    cost_rmb, profit_rmb, price_rmb, price_usd,
    is_remote, has_residential, has_battery,
    is_oversize, oversize_fee, oversize_quantity,
    is_overweight, overweight_fee, overweight_quantity,
    is_moq, moq_value,
    has_pickup_fee, pickup_fee_rmb, pickup_fee_usd,
    is_ddu, is_usd,
    charge_weight, charge_cbm, volume_ratio,
    total_price_usd, total_price_rmb, unit_price_rmb,
    quote_type, notes
) VALUES (
    ?,?,?,?,
    ?,?,
    ?,?,?,?,?,?,
    ?,?,?,
    ?,?,?,?,
    ?,?,?,
    ?,?,?,
    ?,?,?,
    ?,?,
    ?,?,?,
    ?,?,
    ?,?,?,
    ?,?,?,
    ?,?
)
"""


def _insert_full_row_from_payload(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    record_id: str,
    created_at: str,
    updated_at: str,
    source: str = "index",
) -> None:
    src = str(payload.get("_source") or source)
    clean = {k: v for k, v in payload.items() if k != "_source"}
    conn.execute(
        _INSERT_SQL,
        _payload_to_row_tuple(clean, record_id, created_at, updated_at, src),
    )


def _row_to_api_dict(row: sqlite3.Row) -> dict[str, Any]:
    def b(n: str) -> bool:
        return bool(row[n])

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "source": row["source"],
        "customer": row["customer"],
        "productName": row["product_name"],
        "timestamp": row["timestamp"],
        "address": row["address"],
        "postcode": row["postcode"],
        "country": row["country"],
        "deliveryMethod": row["delivery_method"],
        "origin": row["origin"],
        "quantity": float(row["quantity"] or 0),
        "weight": float(row["weight"] or 0),
        "volume": float(row["volume"] or 0),
        "costRmb": float(row["cost_rmb"] or 0),
        "profitRmb": float(row["profit_rmb"] or 0),
        "priceRmb": float(row["price_rmb"] or 0),
        "priceUsd": float(row["price_usd"] or 0),
        "isRemote": b("is_remote"),
        "hasResidential": b("has_residential"),
        "hasBattery": b("has_battery"),
        "isOversize": b("is_oversize"),
        "oversizeFee": float(row["oversize_fee"] or 0),
        "oversizeQuantity": float(row["oversize_quantity"] or 0),
        "isOverweight": b("is_overweight"),
        "overweightFee": float(row["overweight_fee"] or 0),
        "overweightQuantity": float(row["overweight_quantity"] or 0),
        "isMOQ": b("is_moq"),
        "moqValue": float(row["moq_value"] or 0),
        "hasPickupFee": b("has_pickup_fee"),
        "pickupFeeRmb": float(row["pickup_fee_rmb"] or 0),
        "pickupFeeUsd": float(row["pickup_fee_usd"] or 0),
        "isDDU": b("is_ddu"),
        "isUSD": b("is_usd"),
        "chargeWeight": float(row["charge_weight"] or 0),
        "chargeCBM": float(row["charge_cbm"] or 0),
        "volumeRatio": float(row["volume_ratio"] or 0),
        "totalPriceUsd": float(row["total_price_usd"] or 0),
        "totalPriceRmb": float(row["total_price_rmb"] or 0),
        "unitPriceRmb": float(row["unit_price_rmb"] or 0),
        "quoteType": row["quote_type"],
        "notes": row["notes"],
        "channel": row["delivery_method"],
        "amount": float(row["total_price_usd"] or 0),
        "note": row["notes"],
    }


class QuoteHistoryRepository:
    """报价历史表专用仓库；其它业务表各自维护一套模块。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _trim(self) -> None:
        max_n = app_settings_table.get_int_setting(
            self._conn, "quote_history.max_rows", 100
        )
        with self._database.lock:
            to_drop = self._conn.execute(
                f"SELECT id FROM {TABLE_NAME} ORDER BY datetime(updated_at) DESC LIMIT -1 OFFSET ?",
                (max_n,),
            ).fetchall()
            for (drop_id,) in to_drop:
                self._conn.execute(f"DELETE FROM {TABLE_NAME} WHERE id = ?", (drop_id,))
            self._conn.commit()

    def list_rows(self) -> list[dict[str, Any]]:
        with self._database.lock:
            rows = self._conn.execute(
                f"SELECT * FROM {TABLE_NAME} ORDER BY datetime(updated_at) DESC"
            ).fetchall()
            return [_row_to_api_dict(r) for r in rows]

    def insert_from_index_payload(
        self,
        payload: dict[str, Any],
        record_id: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        rid = str(payload.get("id") or record_id or uuid.uuid4())
        now = datetime.now().isoformat(timespec="seconds")
        ca = created_at or now
        ua = updated_at or now
        src = str(payload.get("_source") or "index")
        pl = {k: v for k, v in payload.items() if k != "_source"}
        with self._database.lock:
            self._conn.execute(
                _INSERT_SQL,
                _payload_to_row_tuple(pl, rid, ca, ua, src),
            )
            self._conn.commit()
        self._trim()
        row = self._conn.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (rid,)).fetchone()
        return _row_to_api_dict(row) if row else {}

    def insert_admin_simple(
        self,
        customer: str,
        channel: str,
        amount: float,
        note: str,
        *,
        product_name: str = "00",
        address: str = "",
        country: str = "",
    ) -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")
        rid = str(uuid.uuid4())
        cc = (customer or "").strip()[:500] or "00"
        pn = (product_name or "").strip()[:500] or "00"
        addr = (address or "").strip()[:500]
        ctry = (country or "").strip()[:200]
        payload = {
            "id": rid,
            "timestamp": now,
            "customer": cc,
            "productName": pn,
            "address": addr,
            "country": ctry,
            "deliveryMethod": channel,
            "totalPriceUsd": amount,
            "notes": note,
            "quoteType": "通用",
            "_source": "admin",
        }
        return self.insert_from_index_payload(payload, record_id=rid, created_at=now, updated_at=now)

    def update_admin_simple(
        self,
        item_id: str,
        customer: str,
        channel: str,
        amount: float,
        note: str,
        *,
        product_name: str = "00",
        address: str = "",
        country: str = "",
    ) -> dict[str, Any]:
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT created_at FROM {TABLE_NAME} WHERE id = ?", (item_id,)
            ).fetchone()
            if row is None:
                raise KeyError(item_id)
            now = datetime.now().isoformat(timespec="seconds")
            cc = (customer or "").strip()[:500] or "00"
            pn = (product_name or "").strip()[:500] or "00"
            addr = (address or "").strip()[:500]
            ctry = (country or "").strip()[:200]
            payload = {
                "timestamp": now,
                "customer": cc,
                "productName": pn,
                "address": addr,
                "country": ctry,
                "deliveryMethod": channel,
                "totalPriceUsd": amount,
                "notes": note,
                "quoteType": "通用",
            }
            self._conn.execute(
                _INSERT_SQL,
                _payload_to_row_tuple(payload, item_id, str(row["created_at"]), now, "admin"),
            )
            self._conn.commit()
        self._trim()
        row2 = self._conn.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (item_id,)).fetchone()
        return _row_to_api_dict(row2) if row2 else {}

    def delete(self, item_id: str) -> bool:
        with self._database.lock:
            cur = self._conn.execute(f"DELETE FROM {TABLE_NAME} WHERE id = ?", (item_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def clear(self) -> None:
        with self._database.lock:
            self._conn.execute(f"DELETE FROM {TABLE_NAME}")
            self._conn.commit()
