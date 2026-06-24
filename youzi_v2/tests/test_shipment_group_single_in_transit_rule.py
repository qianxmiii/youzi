"""单票在途到港预警规则评估。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_group_alerts_repository import ShipmentGroupAlertsRepository
from youzi_v2.db.shipment_groups_table import GROUPS_TABLE, MEMBERS_TABLE, RULES_TABLE
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE
from youzi_v2.services.shipment_group_alerts import evaluate_group_alerts
from youzi_v2.shipment_group_rules import RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING


def _seed(db: Database) -> tuple[str, str]:
    now = now_str()
    gid = "group-single-in-transit-test"
    sid = "ship-single-in-transit-test"
    eta = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d 00:00:00")
    with db.lock:
        db.conn.execute(f"DELETE FROM {MEMBERS_TABLE} WHERE group_id = ?", (gid,))
        db.conn.execute(f"DELETE FROM {RULES_TABLE} WHERE group_id = ?", (gid,))
        db.conn.execute(f"DELETE FROM {GROUPS_TABLE} WHERE id = ?", (gid,))
        db.conn.execute(f"DELETE FROM {SHIPMENTS_TABLE} WHERE id = ?", (sid,))
        db.conn.execute(
            f"""
            INSERT INTO {GROUPS_TABLE} (
                id, group_no, group_name, primary_type, customer,
                payment_status, payment_due_rule, note, created_time, updated_time
            ) VALUES (?, 'GTEST001', '', 'MANUAL', 'TestCustomer', 'UNPAID', 'LAST_ARRIVAL', '', ?, ?)
            """,
            (gid, now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, customer, status_code, eta, created_time, updated_time
            ) VALUES (?, 'SN-SINGLE-001', 'TestCustomer', 'IN_TRANSIT', ?, ?, ?)
            """,
            (sid, eta, now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {MEMBERS_TABLE} (
                id, group_id, shipment_id, shipment_no, role, batch_no, created_time
            ) VALUES ('mem-1', ?, ?, 'SN-SINGLE-001', 'NORMAL', '', ?)
            """,
            (gid, sid, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {RULES_TABLE} (
                id, group_id, rule_type, enabled, threshold_days, warning_days,
                trigger_status, config_json, created_time, updated_time
            ) VALUES ('rule-1', ?, ?, 1, NULL, 10, '', '{{}}', ?, ?)
            """,
            (gid, RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING, now, now),
        )
        db.conn.commit()
    return gid, sid


def test_single_in_transit_eta_warning_creates_notification(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    gid, _ = _seed(db)
    repo = ShipmentGroupAlertsRepository(db)

    result = evaluate_group_alerts(db, repo, group_id=gid)

    assert result["created"] == 1
    notifs = repo.list_notifications(gid)
    assert notifs["total"] == 1
    assert notifs["items"][0]["ruleType"] == RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING


def test_single_in_transit_skipped_when_two_in_transit(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    gid, sid = _seed(db)
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, customer, status_code, eta, created_time, updated_time
            ) VALUES ('ship-2', 'SN-SINGLE-002', 'TestCustomer', 'IN_TRANSIT', ?, ?, ?)
            """,
            (now, now, now),
        )
        db.conn.commit()
    repo = ShipmentGroupAlertsRepository(db)

    result = evaluate_group_alerts(db, repo, group_id=gid)

    assert result["created"] == 0
