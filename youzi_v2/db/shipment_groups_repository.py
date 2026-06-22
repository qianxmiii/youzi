"""运单分组 CRUD。"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Any

from .connection import Database
from .datetime_util import now_str
from .shipment_groups_table import GROUPS_TABLE, MEMBERS_TABLE, TYPES_TABLE
from .shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from ..shipment_group_types import (
    GROUP_TYPES as _GROUP_TYPES,
    normalize_types_payload,
    sort_group_types,
)
_PAYMENT_STATUSES = frozenset({"UNPAID", "PARTIAL", "PAID"})
_PAYMENT_DUE_RULES = frozenset({"LAST_ARRIVAL"})
_MEMBER_ROLES = frozenset({"NORMAL", "LAST_BATCH", "KEY_BATCH"})


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    return s if s else None


def _next_group_no(conn: sqlite3.Connection) -> str:
    day = datetime.now().strftime("%Y%m%d")
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


def _primary_from_row(row: sqlite3.Row) -> str:
    keys = row.keys()
    if "primary_type" in keys:
        return (row["primary_type"] or "MANUAL").strip().upper() or "MANUAL"
    if "group_type" in keys:
        return (row["group_type"] or "MANUAL").strip().upper() or "MANUAL"
    return "MANUAL"


def _row_to_api(
    row: sqlite3.Row,
    *,
    member_count: int | None = None,
    group_types: list[str] | None = None,
) -> dict[str, Any]:
    primary = _primary_from_row(row)
    types = sort_group_types(group_types or [primary])
    out: dict[str, Any] = {
        "id": row["id"],
        "groupNo": row["group_no"],
        "groupName": row["group_name"] or "",
        "primaryType": primary,
        "groupTypes": types,
        "groupType": primary,
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
    return out


def _member_to_api(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "groupId": row["group_id"],
        "shipmentId": row["shipment_id"],
        "shipmentNo": row["shipment_no"],
        "role": row["role"],
        "batchNo": row["batch_no"] or "",
        "createdTime": row["created_time"],
    }


class ShipmentGroupsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._database.conn

    def _load_types_for_group(self, group_id: str) -> list[str]:
        gid = group_id.strip()
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT group_type FROM {TYPES_TABLE}
                WHERE group_id = ?
                ORDER BY group_type
                """,
                (gid,),
            ).fetchall()
        return sort_group_types([str(r["group_type"]) for r in rows])

    def _load_types_for_groups(self, group_ids: list[str]) -> dict[str, list[str]]:
        ids = [g.strip() for g in group_ids if g and g.strip()]
        if not ids:
            return {}
        placeholders = ", ".join("?" * len(ids))
        with self._database.lock:
            rows = self._conn.execute(
                f"""
                SELECT group_id, group_type FROM {TYPES_TABLE}
                WHERE group_id IN ({placeholders})
                ORDER BY group_type
                """,
                ids,
            ).fetchall()
        out: dict[str, list[str]] = {gid: [] for gid in ids}
        for row in rows:
            out.setdefault(str(row["group_id"]), []).append(str(row["group_type"]))
        return {gid: sort_group_types(types) for gid, types in out.items()}

    def _replace_group_types(self, group_id: str, group_types: list[str]) -> None:
        gid = group_id.strip()
        types = sort_group_types(group_types)
        if not types:
            raise ValueError("groupTypes 至少包含一项")
        now = now_str()
        with self._database.lock:
            self._conn.execute(
                f"DELETE FROM {TYPES_TABLE} WHERE group_id = ?",
                (gid,),
            )
            for gtype in types:
                self._conn.execute(
                    f"""
                    INSERT INTO {TYPES_TABLE} (id, group_id, group_type, created_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), gid, gtype, now),
                )
            self._conn.commit()

    def _enrich_row_api(
        self,
        row: sqlite3.Row,
        *,
        member_count: int | None = None,
        types_map: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        gid = str(row["id"])
        types = (types_map or {}).get(gid) or self._load_types_for_group(gid)
        if not types:
            types = [_primary_from_row(row)]
        return _row_to_api(row, member_count=member_count, group_types=types)

    def list_rows(
        self,
        *,
        search: str | None = None,
        group_type: str | None = None,
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
        if group_type and group_type.strip():
            gt = group_type.strip().upper()
            if gt not in _GROUP_TYPES:
                raise ValueError(f"groupType 无效：{group_type}")
            conditions.append(
                f"""
                id IN (
                  SELECT group_id FROM {TYPES_TABLE}
                  WHERE group_type = ?
                )
                """
            )
            params.append(gt)
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

        types_map = self._load_types_for_groups([str(r["id"]) for r in rows])

        return {
            "items": [
                self._enrich_row_api(
                    r,
                    member_count=int(r["member_count"] or 0),
                    types_map=types_map,
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
        primary_type: str = "MANUAL",
        group_types: list[str] | None = None,
        group_type: str | None = None,
        customer: str | None = None,
        customer_no: str | None = None,
        vessel_voyage: str | None = None,
        destination_port_code: str | None = None,
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
            primary_type=primary_type,
            group_types=group_types,
            group_type=group_type,
            customer=customer,
            customer_no=customer_no,
            vessel_voyage=vessel_voyage,
            destination_port_code=destination_port_code,
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
        primary_type: str = "MANUAL",
        group_types: list[str] | None = None,
        group_type: str | None = None,
        customer: str | None = None,
        customer_no: str | None = None,
        vessel_voyage: str | None = None,
        destination_port_code: str | None = None,
        payment_status: str = "UNPAID",
        payment_due_rule: str = "LAST_ARRIVAL",
        note: str = "",
    ) -> dict[str, Any]:
        primary, types = normalize_types_payload(
            primary_type=primary_type,
            group_types=group_types,
            legacy_group_type=group_type,
        )
        pstatus = (payment_status or "UNPAID").strip().upper()
        if pstatus not in _PAYMENT_STATUSES:
            raise ValueError(f"paymentStatus 无效：{payment_status}")
        prule = (payment_due_rule or "LAST_ARRIVAL").strip().upper()
        if prule not in _PAYMENT_DUE_RULES:
            raise ValueError(f"paymentDueRule 无效：{payment_due_rule}")

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
                        primary,
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

        self._replace_group_types(rid, types)
        created = self.get_by_id(rid)
        if created is None:
            raise RuntimeError("创建分组后读取失败")
        from .shipment_group_alerts_repository import ShipmentGroupAlertsRepository

        ShipmentGroupAlertsRepository(self._database).ensure_default_rules(
            rid, group_types=types
        )
        return created

    def update(
        self,
        item_id: str,
        *,
        group_name: str | None = None,
        primary_type: str | None = None,
        group_types: list[str] | None = None,
        group_type: str | None = None,
        customer: str | None = None,
        customer_no: str | None = None,
        vessel_voyage: str | None = None,
        destination_port_code: str | None = None,
        payment_status: str | None = None,
        payment_due_rule: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any] | None:
        sets: list[str] = []
        params: list[Any] = []
        types_changed = False
        resolved_types: list[str] | None = None

        if group_name is not None:
            sets.append("group_name = ?")
            params.append(group_name.strip())
        if primary_type is not None or group_types is not None or group_type is not None:
            current = self.get_by_id(item_id.strip(), include_members=False)
            if current is None:
                return None
            merged_primary = primary_type if primary_type is not None else current.get("primaryType")
            merged_types = group_types if group_types is not None else current.get("groupTypes")
            legacy = group_type if group_types is None and primary_type is None else None
            primary, resolved_types = normalize_types_payload(
                primary_type=merged_primary,
                group_types=merged_types,
                legacy_group_type=legacy,
            )
            sets.append("primary_type = ?")
            params.append(primary)
            types_changed = True
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

        if not sets:
            return self.get_by_id(item_id)

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
        if types_changed and resolved_types is not None:
            self._replace_group_types(item_id.strip(), resolved_types)
        updated = self.get_by_id(item_id)
        if updated and types_changed and resolved_types is not None:
            from .shipment_group_alerts_repository import ShipmentGroupAlertsRepository

            ShipmentGroupAlertsRepository(self._database).ensure_default_rules(
                item_id.strip(), group_types=resolved_types
            )
        return updated

    def delete(self, item_id: str) -> bool:
        gid = item_id.strip()
        from .shipment_group_alerts_repository import ShipmentGroupAlertsRepository

        ShipmentGroupAlertsRepository(self._database).delete_for_group(gid)
        with self._database.lock:
            self._conn.execute(
                f"DELETE FROM {TYPES_TABLE} WHERE group_id = ?",
                (gid,),
            )
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
        *,
        role: str = "NORMAL",
        batch_no: str = "",
    ) -> dict[str, Any]:
        gid = group_id.strip()
        if not self._group_exists(gid):
            raise KeyError("分组不存在")
        member_role = (role or "NORMAL").strip().upper()
        if member_role not in _MEMBER_ROLES:
            raise ValueError(f"role 无效：{role}")
        batch = (batch_no or "").strip()
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
