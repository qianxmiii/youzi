"""订单流转本地快照。不读取、不写入 shipments。"""

from __future__ import annotations

from typing import Any

from .connection import Database
from .datetime_util import now_str
from .order_flow_orders_table import LOG_TABLE_NAME, TABLE_NAME

_MINE_PREFIX = "销售-"

# 流转系统节点的业务顺序。未列出的状态排在后面，已结束放最后。
STATUS_FLOW = (
    "销售-集货中-不转运",
    "销售-待补充入库信息",
    "配载-待配载确认配载与报价",
    "销售-待确认入库当日报价",
    "配载-待配载确认优惠申请",
    "跟单-待发承运商预报",
    "调度/跟单-提货中",
    "跟单-待反馈入库数据",
    "销售-待确认入库数据",
    "跟单-待上传入库凭证",
    "销售-待再次确认入库数据",
    "配载-待配载确认入库报价",
    "销售-待确认入库后报价",
    "跟单-待修改卖下家",
)
_STATUS_RANK = {name: index for index, name in enumerate(STATUS_FLOW)}


def status_sort_key(status: str) -> tuple[int, int, str]:
    if status == "已结束":
        return (2, 0, status)
    rank = _STATUS_RANK.get(status)
    if rank is None:
        return (1, 0, status)
    return (0, rank, "")


def warehouse_label(value: Any) -> str:
    text = _text(value)
    if "/" in text:
        return text.split("/", 1)[0].strip()
    return text


def _text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text in {"-", "null", "None"}:
        return ""
    return text


def normalize_remote_order(row: dict[str, Any]) -> dict[str, Any] | None:
    waybill_no = _text(row.get("waybillNo"))
    if not waybill_no:
        return None
    status = _text(row.get("currentStatus"))
    operated = _text(row.get("lastOperateTime")) or _text(row.get("updateTime")) or _text(row.get("createTime"))
    return {
        "waybillNo": waybill_no,
        "customerName": _text(row.get("customerDisplayName")) or _text(row.get("customerName")),
        "currentStatus": status,
        "pieces": _text(row.get("pieces")),
        "weightKg": _text(row.get("totalWeight")),
        "chargeWeightKg": _text(row.get("actualBillingWeight")),
        "volumeCbm": _text(row.get("totalVolume")),
        "productName": _text(row.get("productName")),
        "warehouseName": warehouse_label(row.get("deliveryWarehouse")),
        "countryName": warehouse_label(row.get("destinationCountry")),
        "channelName": warehouse_label(row.get("dpsChannel")),
        "lastOperateTime": operated,
        "mine": status.startswith(_MINE_PREFIX),
    }


def _to_api(row: Any) -> dict[str, Any]:
    return {
        "waybillNo": row["waybill_no"],
        "customerName": row["customer_name"] or "",
        "currentStatus": row["current_status"] or "",
        "previousStatus": row["previous_status"] or "",
        "pieces": row["pieces"] or "",
        "weightKg": row["weight_kg"] or "",
        "chargeWeightKg": row["charge_weight_kg"] or "",
        "volumeCbm": row["volume_cbm"] or "",
        "productName": row["product_name"] or "",
        "warehouseName": warehouse_label(row["warehouse_name"]),
        "countryName": warehouse_label(row["country_name"]) if "country_name" in row.keys() else "",
        "channelName": warehouse_label(row["channel_name"]),
        "lastOperateTime": row["last_operate_time"] or "",
        "previousOperateTime": (
            row["previous_operate_time"] if "previous_operate_time" in row.keys() else ""
        )
        or "",
        "mine": bool(row["mine"]),
        "ended": bool(row["ended"]),
        "statusChanged": bool(row["status_changed"]),
        "statusChangedAt": (
            row["status_changed_at"] if "status_changed_at" in row.keys() else ""
        )
        or "",
        "firstSeenTime": row["first_seen_time"] or "",
        "lastSeenTime": row["last_seen_time"] or "",
        "updatedTime": row["updated_time"] or "",
    }


class OrderFlowRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def apply_snapshot(self, remote_rows: list[dict[str, Any]]) -> dict[str, int]:
        incoming = []
        seen: set[str] = set()
        for row in remote_rows:
            item = normalize_remote_order(row)
            if item is None or item["waybillNo"] in seen:
                continue
            seen.add(item["waybillNo"])
            incoming.append(item)
        now = now_str()
        created = changed = refreshed = ended = 0
        with self._database.lock:
            conn = self._database.conn
            self._backfill_logs_locked(conn, now)
            for item in incoming:
                existing = conn.execute(
                    f"SELECT * FROM {TABLE_NAME} WHERE waybill_no = ?",
                    (item["waybillNo"],),
                ).fetchone()
                if existing is None:
                    conn.execute(
                        f"""
                        INSERT INTO {TABLE_NAME} (
                            waybill_no, customer_name, current_status, previous_status,
                            pieces, weight_kg, charge_weight_kg, volume_cbm,
                            product_name, warehouse_name, country_name, channel_name, last_operate_time,
                            mine, ended, status_changed,
                            first_seen_time, last_seen_time, updated_time
                        ) VALUES (?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?)
                        """,
                        (
                            item["waybillNo"],
                            item["customerName"],
                            item["currentStatus"],
                            item["pieces"],
                            item["weightKg"],
                            item["chargeWeightKg"],
                            item["volumeCbm"],
                            item["productName"],
                            item["warehouseName"],
                            item["countryName"],
                            item["channelName"],
                            item["lastOperateTime"],
                            1 if item["mine"] else 0,
                            now,
                            now,
                            now,
                        ),
                    )
                    self._append_log_locked(
                        conn,
                        item["waybillNo"],
                        item["currentStatus"],
                        item["lastOperateTime"],
                        now,
                    )
                    created += 1
                    continue
                status_changed = existing["current_status"] != item["currentStatus"]
                previous = existing["current_status"] if status_changed else existing["previous_status"]
                previous_time = (
                    existing["last_operate_time"]
                    if status_changed
                    else (existing["previous_operate_time"] if "previous_operate_time" in existing.keys() else "")
                )
                keep_flag = 1 if status_changed or existing["status_changed"] else 0
                changed_at = now if status_changed else (
                    existing["status_changed_at"] if "status_changed_at" in existing.keys() else ""
                )
                conn.execute(
                    f"""
                    UPDATE {TABLE_NAME}
                    SET customer_name = ?, current_status = ?, previous_status = ?,
                        pieces = ?, weight_kg = ?, charge_weight_kg = ?, volume_cbm = ?,
                        product_name = ?, warehouse_name = ?, country_name = ?, channel_name = ?,
                        last_operate_time = ?, previous_operate_time = ?, mine = ?, ended = 0,
                        status_changed = ?, status_changed_at = ?, last_seen_time = ?, updated_time = ?
                    WHERE waybill_no = ?
                    """,
                    (
                        item["customerName"],
                        item["currentStatus"],
                        previous or "",
                        item["pieces"],
                        item["weightKg"],
                        item["chargeWeightKg"],
                        item["volumeCbm"],
                        item["productName"],
                        item["warehouseName"],
                        item["countryName"],
                        item["channelName"],
                        item["lastOperateTime"],
                        previous_time or "",
                        1 if item["mine"] else 0,
                        keep_flag,
                        changed_at or "",
                        now,
                        now,
                        item["waybillNo"],
                    ),
                )
                if status_changed:
                    self._append_log_locked(
                        conn,
                        item["waybillNo"],
                        item["currentStatus"],
                        item["lastOperateTime"],
                        now,
                    )
                    changed += 1
                else:
                    refreshed += 1
            active = conn.execute(
                f"SELECT waybill_no FROM {TABLE_NAME} WHERE ended = 0"
            ).fetchall()
            for row in active:
                if row["waybill_no"] not in seen:
                    conn.execute(
                        f"""
                        UPDATE {TABLE_NAME}
                        SET ended = 1,
                            status_changed = 1,
                            status_changed_at = ?,
                            previous_status = CASE
                                WHEN previous_status = '' THEN current_status
                                ELSE previous_status
                            END,
                            previous_operate_time = CASE
                                WHEN previous_operate_time = '' THEN last_operate_time
                                ELSE previous_operate_time
                            END,
                            updated_time = ?
                        WHERE waybill_no = ?
                        """,
                        (now, now, row["waybill_no"]),
                    )
                    self._append_log_locked(conn, row["waybill_no"], "已结束", "", now)
                    ended += 1
            conn.commit()
        return {
            "remote": len(incoming),
            "created": created,
            "changed": changed,
            "refreshed": refreshed,
            "ended": ended,
        }

    def _append_log_locked(
        self,
        conn,
        waybill_no: str,
        status: str,
        operate_time: str,
        recorded_time: str,
    ) -> None:
        status_text = (status or "").strip()
        if not waybill_no or not status_text:
            return
        last = conn.execute(
            f"""
            SELECT status, operate_time FROM {LOG_TABLE_NAME}
            WHERE waybill_no = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (waybill_no,),
        ).fetchone()
        if last and last["status"] == status_text and (last["operate_time"] or "") == (operate_time or ""):
            return
        conn.execute(
            f"""
            INSERT INTO {LOG_TABLE_NAME} (waybill_no, status, operate_time, recorded_time)
            VALUES (?, ?, ?, ?)
            """,
            (waybill_no, status_text, operate_time or "", recorded_time),
        )

    def _backfill_logs_locked(self, conn, now: str) -> None:
        rows = conn.execute(
            f"""
            SELECT * FROM {TABLE_NAME} AS orders
            WHERE NOT EXISTS (
                SELECT 1 FROM {LOG_TABLE_NAME} AS logs
                WHERE logs.waybill_no = orders.waybill_no
            )
            """
        ).fetchall()
        for row in rows:
            if row["previous_status"]:
                self._append_log_locked(
                    conn,
                    row["waybill_no"],
                    row["previous_status"],
                    row["previous_operate_time"] or "",
                    row["first_seen_time"] or now,
                )
            if row["current_status"]:
                self._append_log_locked(
                    conn,
                    row["waybill_no"],
                    row["current_status"],
                    row["last_operate_time"] or "",
                    row["updated_time"] or now,
                )
            if row["ended"]:
                self._append_log_locked(conn, row["waybill_no"], "已结束", "", now)

    def _label_expr(self, column: str) -> str:
        return (
            f"CASE WHEN instr({column}, '/') > 0 "
            f"THEN trim(substr({column}, 1, instr({column}, '/') - 1)) "
            f"ELSE trim({column}) END"
        )

    def _warehouse_expr(self) -> str:
        return self._label_expr("warehouse_name")

    def list_customers(self) -> list[str]:
        with self._database.lock:
            rows = self._database.conn.execute(
                f"""
                SELECT DISTINCT customer_name FROM {TABLE_NAME}
                WHERE customer_name != ''
                ORDER BY customer_name
                """
            ).fetchall()
        return [row["customer_name"] for row in rows]

    def list_countries(self) -> list[str]:
        expr = self._label_expr("country_name")
        with self._database.lock:
            rows = self._database.conn.execute(
                f"""
                SELECT DISTINCT {expr} AS country_label FROM {TABLE_NAME}
                WHERE {expr} != ''
                ORDER BY country_label
                """
            ).fetchall()
        return [row["country_label"] for row in rows]

    def list_channels(self) -> list[str]:
        expr = self._label_expr("channel_name")
        with self._database.lock:
            rows = self._database.conn.execute(
                f"""
                SELECT DISTINCT {expr} AS channel_label FROM {TABLE_NAME}
                WHERE {expr} != ''
                ORDER BY channel_label
                """
            ).fetchall()
        return [row["channel_label"] for row in rows]

    def list_warehouses(self) -> list[str]:
        expr = self._warehouse_expr()
        with self._database.lock:
            rows = self._database.conn.execute(
                f"""
                SELECT DISTINCT {expr} AS warehouse_label FROM {TABLE_NAME}
                WHERE {expr} != ''
                ORDER BY warehouse_label
                """
            ).fetchall()
        return [row["warehouse_label"] for row in rows]

    def list_statuses(self) -> list[str]:
        with self._database.lock:
            rows = self._database.conn.execute(
                f"""
                SELECT DISTINCT current_status FROM {TABLE_NAME}
                WHERE current_status != ''
                ORDER BY current_status
                """
            ).fetchall()
        return sorted((row["current_status"] for row in rows), key=status_sort_key)

    def status_logs(self, waybill_no: str) -> list[dict[str, str]]:
        key = waybill_no.strip()
        if not key:
            raise ValueError("运单号不能为空")
        now = now_str()
        with self._database.lock:
            conn = self._database.conn
            self._backfill_logs_locked(conn, now)
            conn.commit()
            found = conn.execute(
                f"SELECT 1 FROM {TABLE_NAME} WHERE waybill_no = ?",
                (key,),
            ).fetchone()
            if found is None:
                raise KeyError(key)
            rows = conn.execute(
                f"""
                SELECT status, operate_time, recorded_time
                FROM {LOG_TABLE_NAME}
                WHERE waybill_no = ?
                ORDER BY id
                """,
                (key,),
            ).fetchall()
        return [
            {
                "status": row["status"] or "",
                "operateTime": row["operate_time"] or "",
                "recordedTime": row["recorded_time"] or "",
            }
            for row in rows
        ]

    def _unseen_clause(self, seen_at: str | None) -> tuple[str, list[Any]]:
        seen = (seen_at or "").strip()
        if not seen:
            return "status_changed = 1", []
        return (
            "status_changed = 1 AND status_changed_at > ?",
            [seen],
        )

    def summary(self, seen_at: str | None = None) -> dict[str, int]:
        unseen_sql, unseen_params = self._unseen_clause(seen_at)
        with self._database.lock:
            row = self._database.conn.execute(
                f"""
                SELECT
                    SUM(CASE WHEN mine = 1 AND ended = 0 THEN 1 ELSE 0 END) AS mine_count,
                    SUM(CASE WHEN ended = 0 THEN 1 ELSE 0 END) AS active_count,
                    SUM(CASE WHEN ended = 1 THEN 1 ELSE 0 END) AS ended_count,
                    SUM(CASE WHEN status_changed = 1 AND ended = 0 THEN 1 ELSE 0 END) AS changed_count,
                    SUM(CASE WHEN ended = 0 AND (mine = 1 OR status_changed = 1) THEN 1 ELSE 0 END) AS remind_count,
                    SUM(CASE WHEN {unseen_sql} THEN 1 ELSE 0 END) AS unseen_count
                FROM {TABLE_NAME}
                """,
                unseen_params,
            ).fetchone()
        return {
            "mineCount": int(row["mine_count"] or 0),
            "activeCount": int(row["active_count"] or 0),
            "endedCount": int(row["ended_count"] or 0),
            "changedCount": int(row["changed_count"] or 0),
            "remindCount": int(row["remind_count"] or 0),
            "unseenCount": int(row["unseen_count"] or 0),
        }

    def node_counts(self, seen_at: str | None = None) -> list[dict[str, Any]]:
        unseen_sql, unseen_params = self._unseen_clause(seen_at)
        sql = f"""
            SELECT
                CASE WHEN ended = 1 THEN '已结束' ELSE current_status END AS status_name,
                COUNT(*) AS total_count,
                SUM(CASE WHEN {unseen_sql} THEN 1 ELSE 0 END) AS unseen_count
            FROM {TABLE_NAME}
            WHERE ended = 0 OR ({unseen_sql})
            GROUP BY status_name
            ORDER BY unseen_count DESC, total_count DESC, status_name
        """
        params = [*unseen_params, *unseen_params]
        with self._database.lock:
            rows = self._database.conn.execute(sql, params).fetchall()
        items = [
            {
                "status": row["status_name"] or "未填状态",
                "count": int(row["total_count"] or 0),
                "unseen": int(row["unseen_count"] or 0),
            }
            for row in rows
            if int(row["total_count"] or 0) > 0
        ]
        items.sort(key=lambda item: status_sort_key(item["status"]))
        return items

    def list_rows(
        self,
        *,
        scope: str = "active",
        search: str = "",
        status: str = "",
        customer: str = "",
        warehouse: str = "",
        country: str = "",
        channel: str = "",
    ) -> list[dict[str, Any]]:
        clauses = ["1 = 1"]
        params: list[Any] = []
        if scope == "mine":
            clauses.append("mine = 1 AND ended = 0")
        elif scope == "remind":
            clauses.append("ended = 0 AND (mine = 1 OR status_changed = 1)")
        elif scope == "ended":
            clauses.append("ended = 1")
        elif scope != "all":
            clauses.append("ended = 0")
        status_text = status.strip()
        if status_text == "已结束":
            clauses.append("ended = 1")
        elif status_text:
            clauses.append("ended = 0 AND current_status = ?")
            params.append(status_text)
        customer_text = customer.strip()
        if customer_text:
            clauses.append("customer_name = ?")
            params.append(customer_text)
        warehouse_text = warehouse.strip()
        if warehouse_text:
            clauses.append(f"{self._warehouse_expr()} = ?")
            params.append(warehouse_text)
        country_text = country.strip()
        if country_text:
            country_expr = self._label_expr("country_name")
            clauses.append(f"{country_expr} = ?")
            params.append(country_text)
        channel_labels = [part.strip() for part in channel.split(",") if part.strip()]
        if channel_labels:
            placeholders = ", ".join("?" for _ in channel_labels)
            clauses.append(f"{self._label_expr('channel_name')} IN ({placeholders})")
            params.extend(channel_labels)
        text = search.strip()
        if text:
            like = f"%{text}%"
            clauses.append(
                "(waybill_no LIKE ? OR customer_name LIKE ? OR current_status LIKE ? "
                "OR product_name LIKE ? OR warehouse_name LIKE ? OR channel_name LIKE ?)"
            )
            params.extend([like, like, like, like, like, like])
        sql = f"""
            SELECT * FROM {TABLE_NAME}
            WHERE {' AND '.join(clauses)}
            ORDER BY ended ASC, mine DESC, status_changed DESC, updated_time DESC
        """
        with self._database.lock:
            conn = self._database.conn
            self._backfill_logs_locked(conn, now_str())
            conn.commit()
            rows = conn.execute(sql, params).fetchall()
        return [_to_api(row) for row in rows]
