"""运单分组 CRUD。"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .shipment_groups_table import GROUPS_TABLE, MEMBERS_TABLE, NOTIFICATIONS_TABLE, RULES_TABLE
from .shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from ..shipment_group_rules import validate_rule_payload
_PAYMENT_STATUSES = frozenset({"UNPAID", "PARTIAL", "PAID"})
_PAYMENT_DUE_RULES = frozenset({"LAST_ARRIVAL"})
_MEMBER_ROLES = frozenset({"NORMAL", "LAST_BATCH", "KEY_BATCH"})


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    return s if s else None


import re

_GROUP_NO_LEGACY = re.compile(r"^G20(\d{9})$")


def format_group_no_display(group_no: str | None) -> str:
    """旧自动编号 G20YYMMDDnnn → 展示 GYYMMDDnnn。"""
    s = (group_no or "").strip()
    m = _GROUP_NO_LEGACY.match(s)
    return f"G{m.group(1)}" if m else s


def _next_group_no(conn: sqlite3.Connection) -> str:
    day = datetime.now().strftime("%y%m%d")
    prefix = f"G{day}"
    row = conn.execute(
        f"""
        SELECT group_no FROM {GROUPS_TABLE}
        WHERE group_no LIKE ?
        ORDER BY group_no DESC
        LIMIT 1
        """,
        (f"{prefix}%",),
    ).fetchone()
    seq = 1
    if row:
        tail = str(row["group_no"])[len(prefix) :]
        try:
            seq = int(tail) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:03d}"


def _row_to_api(
    row: sqlite3.Row,
    *,
    member_count: int | None = None,
    enabled_rules: list[str] | None = None,
    unread_notification_count: int | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row["id"],
        "groupNo": row["group_no"],
        "groupName": row["group_name"] or "",
        "customer": row["customer"],
        "customerNo": row["customer_no"],
        "vesselVoyage": row["vessel_voyage"],
        "destinationPortCode": row["destination_port_code"],
        "paymentStatus": row["payment_status"],
        "paymentDueRule": row["payment_due_rule"],
        "note": row["note"] or "",
        "createdTime": row["created_time"],
        "updatedTime": row["updated_time"],
    }
    if member_count is not None:
        out["memberCount"] = member_count
    if enabled_rules is not None:
        out["enabledRules"] = enabled_rules
    if unread_notification_count is not None:
        out["unreadNotificationCount"] = unread_notification_count
    return out


def _member_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "groupId": row["group_id"],
        "shipmentId": row["shipment_id"],
        "shipmentNo": row["shipment_no"],
        "createdTime": row["created_time"],
    }


class ShipmentGroupsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _load_enabled_rules_for_groups(self, group_ids: list[str]) -> dict[str, list[str]]:
        ids = [g.strip() for g in group_ids if g and g.strip()]
        if not ids:
            return {}
        placeholders = ", ".join("?" * len(ids))
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT group_id, rule_type FROM {RULES_TABLE}
                WHERE group_id IN ({placeholders}) AND enabled = 1
                ORDER BY rule_type
                """,
                ids,
            ).fetchall()
        out: dict[str, list[str]] = {gid: [] for gid in ids}
        for row in rows:
            out.setdefault(str(row["group_id"]), []).append(str(row["rule_type"]))
        return out

    def _load_unread_counts_for_groups(self, group_ids: list[str]) -> dict[str, int]:
        ids = [g.strip() for g in group_ids if g and g.strip()]
        if not ids:
            return {}
        placeholders = ", ".join("?" * len(ids))
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT group_id, COUNT(*) AS c
                FROM {NOTIFICATIONS_TABLE}
                WHERE group_id IN ({placeholders})
                  AND (read_at IS NULL OR TRIM(read_at) = '')
                  AND (resolved_at IS NULL OR TRIM(resolved_at) = '')
                GROUP BY group_id
                """,
                ids,
            ).fetchall()
        return {str(r["group_id"]): int(r["c"] or 0) for r in rows}

    def _enrich_row_api(
        self,
        row: sqlite3.Row,
        *,
        member_count: int | None = None,
        rules_map: dict[str, list[str]] | None = None,
        unread_map: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        gid = str(row["id"])
        enabled = (rules_map or {}).get(gid)
        if enabled is None:
            enabled = self._load_enabled_rules_for_groups([gid]).get(gid, [])
        unread = (unread_map or {}).get(gid, 0) if unread_map is not None else None
        return _row_to_api(
            row,
            member_count=member_count,
            enabled_rules=enabled,
            unread_notification_count=unread,
        )

    def list_rows(
        self,
        *,
        search: str | None = None,
        rule_type: str | None = None,
        has_rule: bool | None = None,
        has_unread: bool | None = None,
        payment_status: str | None = None,
        customer: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        conditions: list[str] = []
        params: list[Any] = []

        if search and search.strip():
            q = f"%{search.strip()}%"
            conditions.append(
                "(group_no LIKE ? OR group_name LIKE ? OR customer LIKE ? OR customer_no LIKE ?)"
            )
            params.extend([q, q, q, q])
        if rule_type and rule_type.strip():
            from ..shipment_group_rules import normalize_rule_type

            rt = normalize_rule_type(rule_type)
            conditions.append(
                f"""
                id IN (
                  SELECT group_id FROM {RULES_TABLE}
                  WHERE rule_type = ? AND enabled = 1
                )
                """
            )
            params.append(rt)
        elif has_rule is True:
            conditions.append(
                f"""
                id IN (
                  SELECT DISTINCT group_id FROM {RULES_TABLE}
                  WHERE enabled = 1
                )
                """
            )
        elif has_rule is False:
            conditions.append(
                f"""
                id NOT IN (
                  SELECT DISTINCT group_id FROM {RULES_TABLE}
                  WHERE enabled = 1
                )
                """
            )
        if has_unread is True:
            conditions.append(
                f"""
                id IN (
                  SELECT DISTINCT group_id FROM {NOTIFICATIONS_TABLE}
                  WHERE (read_at IS NULL OR TRIM(read_at) = '')
                    AND (resolved_at IS NULL OR TRIM(resolved_at) = '')
                )
                """
            )
        elif has_unread is False:
            conditions.append(
                f"""
                id NOT IN (
                  SELECT DISTINCT group_id FROM {NOTIFICATIONS_TABLE}
                  WHERE (read_at IS NULL OR TRIM(read_at) = '')
                    AND (resolved_at IS NULL OR TRIM(resolved_at) = '')
                )
                """
            )
        if payment_status and payment_status.strip():
            conditions.append("payment_status = ?")
            params.append(payment_status.strip().upper())
        if customer and customer.strip():
            conditions.append("TRIM(customer) = ?")
            params.append(customer.strip())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._database.lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) AS c FROM {GROUPS_TABLE} {where}",
                params,
            ).fetchone()["c"]
            rows = self._conn.execute(
                f"""
                SELECT g.*,
                    (
                        SELECT COUNT(*) FROM {MEMBERS_TABLE} m
                        WHERE m.group_id = g.id
                    ) AS member_count
                FROM {GROUPS_TABLE} g
                {where}
                ORDER BY datetime(g.updated_time) DESC, g.group_no DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        rules_map = self._load_enabled_rules_for_groups([str(r["id"]) for r in rows])
        unread_map = self._load_unread_counts_for_groups([str(r["id"]) for r in rows])

        return {
            "items": [
                self._enrich_row_api(
                    r,
                    member_count=int(r["member_count"] or 0),
                    rules_map=rules_map,
                    unread_map=unread_map,
                )
                for r in rows
            ],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    def _group_exists(self, group_id: str) -> bool:
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT 1 FROM {GROUPS_TABLE} WHERE id = ?",
                (group_id.strip(),),
            ).fetchone()
        return row is not None

    def get_by_group_no(self, group_no: str) -> dict[str, Any] | None:
        gn = (group_no or "").strip()
        if not gn:
            return None
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT g.*,
                    (
                        SELECT COUNT(*) FROM {MEMBERS_TABLE} m
                        WHERE m.group_id = g.id
                    ) AS member_count
                FROM {GROUPS_TABLE} g
                WHERE g.group_no = ? COLLATE NOCASE
                """,
                (gn,),
            ).fetchone()
        if not row:
            return None
        return self._enrich_row_api(row, member_count=int(row["member_count"] or 0))

    def get_or_create_for_import(
        self,
        group_no: str,
        *,
        group_name: str = "",
        customer: str | None = None,
        customer_no: str | None = None,
        vessel_voyage: str | None = None,
        destination_port_code: str | None = None,
        rules: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], bool]:
        gn = (group_no or "").strip()
        if not gn:
            raise ValueError("分组编号不能为空")
        existing = self.get_by_group_no(gn)
        if existing:
            patch: dict[str, Any] = {}
            if (group_name or "").strip() and not (existing.get("groupName") or "").strip():
                patch["group_name"] = group_name.strip()
            if customer and not existing.get("customer"):
                patch["customer"] = customer
            if customer_no and not existing.get("customerNo"):
                patch["customer_no"] = customer_no
            if vessel_voyage and not existing.get("vesselVoyage"):
                patch["vessel_voyage"] = vessel_voyage
            if destination_port_code and not existing.get("destinationPortCode"):
                patch["destination_port_code"] = destination_port_code
            if patch:
                updated = self.update(existing["id"], **patch)
                return (updated or existing), False
            return existing, False
        created = self.create(
            group_no=gn,
            group_name=group_name,
            customer=customer,
            customer_no=customer_no,
            vessel_voyage=vessel_voyage,
            destination_port_code=destination_port_code,
            rules=rules,
        )
        return created, True

    def _touch_group(self, group_id: str) -> None:
        with self._database.lock:
            self._conn.execute(
                f"UPDATE {GROUPS_TABLE} SET updated_time = ? WHERE id = ?",
                (now_str(), group_id.strip()),
            )
            self._conn.commit()

    def _list_member_rows(self, group_id: str) -> list[sqlite3.Row]:
        with self._database.lock:
            return self._conn.execute(
                f"""
                SELECT * FROM {MEMBERS_TABLE}
                WHERE group_id = ?
                ORDER BY datetime(created_time) ASC, shipment_no ASC
                """,
                (group_id.strip(),),
            ).fetchall()

    def _resolve_shipment(self, shipment_id: str) -> tuple[str, str] | None:
        sid = shipment_id.strip()
        if not sid:
            return None
        with self._database.lock:
            row = self._conn.execute(
                f"SELECT id, shipment_no FROM {SHIPMENTS_TABLE} WHERE id = ?",
                (sid,),
            ).fetchone()
        if not row:
            return None
        return str(row["id"]), str(row["shipment_no"])

    def get_by_id(self, item_id: str, *, include_members: bool = True) -> dict[str, Any] | None:
        gid = item_id.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT g.*,
                    (
                        SELECT COUNT(*) FROM {MEMBERS_TABLE} m
                        WHERE m.group_id = g.id
                    ) AS member_count
                FROM {GROUPS_TABLE} g
                WHERE g.id = ?
                """,
                (gid,),
            ).fetchone()
        if not row:
            return None
        out = self._enrich_row_api(row, member_count=int(row["member_count"] or 0))
        if include_members:
            out["members"] = [
                _member_to_api(r) for r in self._list_member_rows(gid)
            ]
            out.update(self._member_stats(gid))
        from .shipment_group_alerts_repository import ShipmentGroupAlertsRepository

        alerts_repo = ShipmentGroupAlertsRepository(self._database)
        out["unreadNotificationCount"] = alerts_repo.count_unread(gid)
        out["rules"] = alerts_repo.list_rules(gid)
        return out

    def _member_stats(self, group_id: str) -> dict[str, int]:
        gid = group_id.strip()
        with self._database.lock:
            row = self._conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN TRIM(COALESCE(s.ata, '')) != '' THEN 1 ELSE 0 END) AS arrived,
                    SUM(
                        CASE
                            WHEN UPPER(COALESCE(s.status_code, '')) = 'DELIVERED'
                              OR TRIM(COALESCE(s.delivered_time, '')) != ''
                            THEN 1 ELSE 0
                        END
                    ) AS delivered
                FROM {MEMBERS_TABLE} m
                INNER JOIN {SHIPMENTS_TABLE} s ON s.id = m.shipment_id
                WHERE m.group_id = ?
                """,
                (gid,),
            ).fetchone()
        total = int(row["total"] or 0)
        delivered = int(row["delivered"] or 0)
        return {
            "arrivedCount": int(row["arrived"] or 0),
            "deliveredCount": delivered,
            "undeliveredCount": max(0, total - delivered),
        }

    def create(
        self,
        *,
        group_no: str | None = None,
        group_name: str = "",
        customer: str | None = None,
        customer_no: str | None = None,
        vessel_voyage: str | None = None,
        destination_port_code: str | None = None,
        payment_status: str = "UNPAID",
        payment_due_rule: str = "LAST_ARRIVAL",
        note: str = "",
        rules: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        pstatus = (payment_status or "UNPAID").strip().upper()
        if pstatus not in _PAYMENT_STATUSES:
            raise ValueError(f"paymentStatus 无效：{payment_status}")
        prule = (payment_due_rule or "LAST_ARRIVAL").strip().upper()
        if prule not in _PAYMENT_DUE_RULES:
            raise ValueError(f"paymentDueRule 无效：{payment_due_rule}")

        normalized_rules: list[dict[str, Any]] = []
        if rules:
            seen: set[str] = set()
            for raw in rules:
                validated = validate_rule_payload(
                    str(raw.get("ruleType") or raw.get("rule_type") or ""),
                    raw,
                )
                rt = validated["ruleType"]
                if rt in seen:
                    raise ValueError(f"规则重复：{rt}")
                seen.add(rt)
                normalized_rules.append(validated)

        rid = str(uuid.uuid4())
        now = now_str()
        with self._database.lock:
            no = (group_no or "").strip() or _next_group_no(self._conn)
            try:
                self._conn.execute(
                    f"""
                    INSERT INTO {GROUPS_TABLE} (
                        id, group_no, group_name, primary_type,
                        customer, customer_no, vessel_voyage, destination_port_code,
                        payment_status, payment_due_rule, note,
                        created_time, updated_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rid,
                        no,
                        (group_name or "").strip(),
                        "",
                        _normalize_optional(customer),
                        _normalize_optional(customer_no),
                        _normalize_optional(vessel_voyage),
                        _normalize_optional(destination_port_code),
                        pstatus,
                        prule,
                        (note or "").strip(),
                        now,
                        now,
                    ),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"分组编号已存在：{no}") from exc

        if normalized_rules:
            from .shipment_group_alerts_repository import ShipmentGroupAlertsRepository

            ShipmentGroupAlertsRepository(self._database).replace_rules(rid, normalized_rules)
        created = self.get_by_id(rid)
        if created is None:
            raise RuntimeError("创建分组后读取失败")
        return created

    def update(
        self,
        item_id: str,
        *,
        group_name: str | None = None,
        customer: str | None = None,
        customer_no: str | None = None,
        vessel_voyage: str | None = None,
        destination_port_code: str | None = None,
        payment_status: str | None = None,
        payment_due_rule: str | None = None,
        note: str | None = None,
        rules: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        sets: list[str] = []
        params: list[Any] = []
        if group_name is not None:
            sets.append("group_name = ?")
            params.append(group_name.strip())
        if customer is not None:
            sets.append("customer = ?")
            params.append(_normalize_optional(customer))
        if customer_no is not None:
            sets.append("customer_no = ?")
            params.append(_normalize_optional(customer_no))
        if vessel_voyage is not None:
            sets.append("vessel_voyage = ?")
            params.append(_normalize_optional(vessel_voyage))
        if destination_port_code is not None:
            sets.append("destination_port_code = ?")
            params.append(_normalize_optional(destination_port_code))
        if payment_status is not None:
            pstatus = payment_status.strip().upper()
            if pstatus not in _PAYMENT_STATUSES:
                raise ValueError(f"paymentStatus 无效：{payment_status}")
            sets.append("payment_status = ?")
            params.append(pstatus)
        if payment_due_rule is not None:
            prule = payment_due_rule.strip().upper()
            if prule not in _PAYMENT_DUE_RULES:
                raise ValueError(f"paymentDueRule 无效：{payment_due_rule}")
            sets.append("payment_due_rule = ?")
            params.append(prule)
        if note is not None:
            sets.append("note = ?")
            params.append(note.strip())

        if not sets and rules is None:
            return self.get_by_id(item_id)

        if sets:
            sets.append("updated_time = ?")
            params.append(now_str())
            params.append(item_id.strip())

            with self._database.lock:
                cur = self._conn.execute(
                    f"UPDATE {GROUPS_TABLE} SET {', '.join(sets)} WHERE id = ?",
                    params,
                )
                if cur.rowcount == 0:
                    return None
                self._conn.commit()

        if rules is not None:
            from .shipment_group_alerts_repository import ShipmentGroupAlertsRepository

            normalized: list[dict[str, Any]] = []
            seen: set[str] = set()
            for raw in rules:
                validated = validate_rule_payload(
                    str(raw.get("ruleType") or raw.get("rule_type") or ""),
                    raw,
                )
                rt = validated["ruleType"]
                if rt in seen:
                    raise ValueError(f"规则重复：{rt}")
                seen.add(rt)
                normalized.append(validated)
            ShipmentGroupAlertsRepository(self._database).replace_rules(
                item_id.strip(), normalized
            )
        return self.get_by_id(item_id)

    def delete(self, item_id: str) -> bool:
        gid = item_id.strip()
        from .shipment_group_alerts_repository import ShipmentGroupAlertsRepository

        ShipmentGroupAlertsRepository(self._database).delete_for_group(gid)
        with self._database.lock:
            self._conn.execute(
                f"DELETE FROM {MEMBERS_TABLE} WHERE group_id = ?",
                (gid,),
            )
            cur = self._conn.execute(
                f"DELETE FROM {GROUPS_TABLE} WHERE id = ?",
                (gid,),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def add_members(
        self,
        group_id: str,
        shipment_ids: list[str],
    ) -> dict[str, Any]:
        gid = group_id.strip()
        if not self._group_exists(gid):
            raise KeyError("分组不存在")
        member_role = "NORMAL"
        batch = ""
        now = now_str()

        unique_ids = list(dict.fromkeys(s.strip() for s in shipment_ids if s and s.strip()))
        added = 0
        skipped = 0
        errors: list[dict[str, str]] = []

        with self._database.lock:
            for sid in unique_ids:
                resolved = self._resolve_shipment(sid)
                if resolved is None:
                    errors.append(
                        {"shipmentId": sid, "shipmentNo": "", "message": "运单不存在"}
                    )
                    continue
                ship_id, ship_no = resolved
                existing = self._conn.execute(
                    f"""
                    SELECT id FROM {MEMBERS_TABLE}
                    WHERE group_id = ? AND shipment_id = ?
                    """,
                    (gid, ship_id),
                ).fetchone()
                if existing:
                    skipped += 1
                    continue
                try:
                    self._conn.execute(
                        f"""
                        INSERT INTO {MEMBERS_TABLE} (
                            id, group_id, shipment_id, shipment_no,
                            role, batch_no, created_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            gid,
                            ship_id,
                            ship_no,
                            member_role,
                            batch,
                            now,
                        ),
                    )
                    added += 1
                except sqlite3.IntegrityError:
                    skipped += 1
            if added:
                self._conn.execute(
                    f"UPDATE {GROUPS_TABLE} SET updated_time = ? WHERE id = ?",
                    (now, gid),
                )
            self._conn.commit()

        total = len(unique_ids)
        failed = len(errors)
        return {
            "total": total,
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "errors": errors,
        }

    def remove_members(
        self,
        group_id: str,
        shipment_ids: list[str],
    ) -> dict[str, Any]:
        gid = group_id.strip()
        if not self._group_exists(gid):
            raise KeyError("分组不存在")

        unique_ids = list(dict.fromkeys(s.strip() for s in shipment_ids if s and s.strip()))
        removed = 0
        not_found = 0
        errors: list[dict[str, str]] = []

        with self._database.lock:
            for sid in unique_ids:
                resolved = self._resolve_shipment(sid)
                if resolved is None:
                    not_found += 1
                    errors.append(
                        {"shipmentId": sid, "shipmentNo": "", "message": "运单不存在"}
                    )
                    continue
                ship_id, ship_no = resolved
                cur = self._conn.execute(
                    f"""
                    DELETE FROM {MEMBERS_TABLE}
                    WHERE group_id = ? AND shipment_id = ?
                    """,
                    (gid, ship_id),
                )
                if cur.rowcount:
                    removed += 1
                else:
                    not_found += 1
                    errors.append(
                        {
                            "shipmentId": ship_id,
                            "shipmentNo": ship_no,
                            "message": "不在该分组中",
                        }
                    )
            if removed:
                self._conn.execute(
                    f"UPDATE {GROUPS_TABLE} SET updated_time = ? WHERE id = ?",
                    (now_str(), gid),
                )
            self._conn.commit()

        return {
            "total": len(unique_ids),
            "removed": removed,
            "notFound": not_found,
            "errors": errors,
        }

    def patch_members_batch(
        self,
        group_id: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        gid = group_id.strip()
        if not self._group_exists(gid):
            raise KeyError("分组不存在")

        updated = 0
        not_found = 0
        skipped = 0
        errors: list[dict[str, str]] = []
        now = now_str()

        with self._database.lock:
            for item in items:
                sid = str(item.get("shipment_id") or "").strip()
                if not sid:
                    skipped += 1
                    continue
                resolved = self._resolve_shipment(sid)
                if resolved is None:
                    not_found += 1
                    errors.append(
                        {"shipmentId": sid, "shipmentNo": "", "message": "运单不存在"}
                    )
                    continue
                ship_id, ship_no = resolved
                member = self._conn.execute(
                    f"""
                    SELECT id FROM {MEMBERS_TABLE}
                    WHERE group_id = ? AND shipment_id = ?
                    """,
                    (gid, ship_id),
                ).fetchone()
                if not member:
                    not_found += 1
                    errors.append(
                        {
                            "shipmentId": ship_id,
                            "shipmentNo": ship_no,
                            "message": "不在该分组中",
                        }
                    )
                    continue

                sets: list[str] = []
                params: list[Any] = []
                role = item.get("role")
                batch_no = item.get("batch_no")
                if role is not None:
                    member_role = str(role).strip().upper()
                    if member_role not in _MEMBER_ROLES:
                        errors.append(
                            {
                                "shipmentId": ship_id,
                                "shipmentNo": ship_no,
                                "message": f"role 无效：{role}",
                            }
                        )
                        skipped += 1
                        continue
                    sets.append("role = ?")
                    params.append(member_role)
                if batch_no is not None:
                    sets.append("batch_no = ?")
                    params.append(str(batch_no).strip())
                if not sets:
                    skipped += 1
                    continue
                params.extend([gid, ship_id])
                cur = self._conn.execute(
                    f"""
                    UPDATE {MEMBERS_TABLE}
                    SET {', '.join(sets)}
                    WHERE group_id = ? AND shipment_id = ?
                    """,
                    params,
                )
                if cur.rowcount:
                    updated += 1

            if updated:
                self._conn.execute(
                    f"UPDATE {GROUPS_TABLE} SET updated_time = ? WHERE id = ?",
                    (now, gid),
                )
            self._conn.commit()

        return {
            "total": len(items),
            "updated": updated,
            "notFound": not_found,
            "skipped": skipped,
            "errors": errors,
        }
