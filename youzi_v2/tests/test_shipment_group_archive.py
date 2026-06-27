"""运单分组归档。"""

from __future__ import annotations

from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_groups_repository import ShipmentGroupsRepository
from youzi_v2.db.shipment_groups_table import GROUPS_TABLE, MEMBERS_TABLE, ensure_schema
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from youzi_v2.services.shipment_group_archive import run_group_auto_archive_batch


def _seed_group(
    db: Database,
    *,
    gid: str,
    payment_status: str,
    delivered: bool,
) -> None:
    now = now_str()
    sid = f"ship-{gid}"
    status = "DELIVERED" if delivered else "IN_TRANSIT"
    delivered_time = now if delivered else None
    with db.lock:
        db.conn.execute(f"DELETE FROM {MEMBERS_TABLE} WHERE group_id = ?", (gid,))
        db.conn.execute(f"DELETE FROM {GROUPS_TABLE} WHERE id = ?", (gid,))
        db.conn.execute(f"DELETE FROM {SHIPMENTS_TABLE} WHERE id = ?", (sid,))
        db.conn.execute(
            f"""
            INSERT INTO {GROUPS_TABLE} (
                id, group_no, group_name, primary_type, customer,
                payment_status, payment_due_rule, note, archived_at, created_time, updated_time
            ) VALUES (?, ?, '', 'MANUAL', 'C1', ?, 'LAST_ARRIVAL', '', '', ?, ?)
            """,
            (gid, f"G-{gid}", payment_status, now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, customer, status_code, delivered_time, created_time, updated_time
            ) VALUES (?, ?, 'C1', ?, ?, ?, ?)
            """,
            (sid, f"SN-{gid}", status, delivered_time, now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {MEMBERS_TABLE} (
                id, group_id, shipment_id, shipment_no, role, batch_no, created_time
            ) VALUES ('mem-{gid}', ?, ?, ?, 'NORMAL', '', ?)
            """,
            (gid, sid, f"SN-{gid}", now),
        )
        db.conn.commit()


def test_manual_archive_and_unarchive(tmp_path: Path) -> None:
    db = Database(tmp_path / "archive.db")
    ensure_schema(db.conn)
    repo = ShipmentGroupsRepository(db)
    _seed_group(db, gid="g1", payment_status="UNPAID", delivered=False)

    archived = repo.archive("g1")
    assert archived is not None
    assert archived["archivedAt"]

    active = repo.list_rows(archived=False)
    assert active["total"] == 0

    archived_list = repo.list_rows(archived=True)
    assert archived_list["total"] == 1

    restored = repo.unarchive("g1")
    assert restored is not None
    assert not restored.get("archivedAt")


def test_auto_archive_only_when_all_delivered_and_paid(tmp_path: Path) -> None:
    db = Database(tmp_path / "auto.db")
    ensure_schema(db.conn)
    repo = ShipmentGroupsRepository(db)
    _seed_group(db, gid="paid-done", payment_status="PAID", delivered=True)
    _seed_group(db, gid="paid-open", payment_status="PAID", delivered=False)
    _seed_group(db, gid="unpaid-done", payment_status="UNPAID", delivered=True)

    candidates = repo.list_auto_archive_candidate_ids()
    assert candidates == ["paid-done"]

    result = run_group_auto_archive_batch(repo, force=True, trigger="manual")
    assert result["archived"] == 1

    active = repo.list_rows(archived=False)
    assert active["total"] == 2
    assert not any(item["id"] == "paid-done" for item in active["items"])
