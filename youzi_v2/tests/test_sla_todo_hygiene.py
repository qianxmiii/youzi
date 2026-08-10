"""运输时效待办：孤儿清理、同单去重、按运单合并。"""

from __future__ import annotations

import uuid
from pathlib import Path

from youzi_v2.db.channel_sla_rules_repository import ChannelSlaRulesRepository
from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_exception_followup_repository import (
    ShipmentExceptionFollowupRepository,
)
from youzi_v2.db.shipment_sla import ALERT_WAREHOUSE_NO_DEPARTURE, RISK_OVERDUE
from youzi_v2.db.shipment_sla_alerts_repository import ShipmentSlaAlertsRepository
from youzi_v2.db.shipment_sla_alerts_table import ensure_schema as ensure_alerts_schema
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE, ensure_schema as ensure_shipments_schema
from youzi_v2.services.shipment_sla_scan import scan_shipment_sla_alerts


def _prep(tmp_path: Path) -> tuple[Database, ShipmentSlaAlertsRepository]:
    db = Database(tmp_path / "sla_todo.db")
    ensure_shipments_schema(db.conn)
    ensure_alerts_schema(db.conn)
    return db, ShipmentSlaAlertsRepository(db)


def test_resolve_orphan_and_dedupe_on_scan(tmp_path: Path) -> None:
    db, alerts = _prep(tmp_path)
    now = now_str()
    live_id = str(uuid.uuid4())
    orphan_id = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, channel_code, warehouse_entry_time,
                created_time, updated_time
            ) VALUES (?, 'SN-LIVE', 'CH1', '2026-06-01', ?, ?)
            """,
            (live_id, now, now),
        )
        for sid, aid in ((orphan_id, str(uuid.uuid4())), (live_id, str(uuid.uuid4()))):
            db.conn.execute(
                f"""
                INSERT INTO shipment_sla_alerts (
                    id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                    due_date, event_key, created_time, updated_time
                ) VALUES (?, ?, 'SN-LIVE', ?, ?, 'open', 'warning', '2026-06-08', ?, ?, ?)
                """,
                (
                    aid,
                    sid,
                    ALERT_WAREHOUSE_NO_DEPARTURE,
                    RISK_OVERDUE,
                    f"{sid}|WAREHOUSE_NO_DEPARTURE|2026-06-01",
                    now,
                    now,
                ),
            )
        # 同 live 再插一条同类型重复
        db.conn.execute(
            f"""
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                due_date, event_key, created_time, updated_time
            ) VALUES (?, ?, 'SN-LIVE', ?, ?, 'open', 'warning', '2026-06-08', ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                live_id,
                ALERT_WAREHOUSE_NO_DEPARTURE,
                RISK_OVERDUE,
                f"{live_id}|WAREHOUSE_NO_DEPARTURE|dup",
                now,
                now,
            ),
        )
        db.conn.commit()

    result = scan_shipment_sla_alerts(
        alerts,
        ChannelSlaRulesRepository(db),
        ShipmentExceptionFollowupRepository(db),
        force=True,
        trigger="manual",
    )
    assert result["skipped"] is False

    open_rows = db.conn.execute(
        """
        SELECT shipment_id, shipment_no, status FROM shipment_sla_alerts
        WHERE status = 'open' AND alert_type = ?
        """,
        (ALERT_WAREHOUSE_NO_DEPARTURE,),
    ).fetchall()
    assert len(open_rows) == 1
    assert open_rows[0]["shipment_id"] == live_id
    assert open_rows[0]["shipment_no"] == "SN-LIVE"


def test_todo_notifications_merge_by_shipment(tmp_path: Path) -> None:
    db, alerts = _prep(tmp_path)
    now = now_str()
    sid = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, channel_code, created_time, updated_time
            ) VALUES (?, 'SN-MERGE', 'CH1', ?, ?)
            """,
            (sid, now, now),
        )
        for at, due in (
            ("WAREHOUSE_NO_DEPARTURE", "2026-06-01"),
            ("ARRIVAL_NO_DELIVERY", "2026-06-10"),
        ):
            db.conn.execute(
                f"""
                INSERT INTO shipment_sla_alerts (
                    id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                    due_date, event_key, created_time, updated_time
                ) VALUES (?, ?, 'SN-MERGE', ?, ?, 'open', 'warning', ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    sid,
                    at,
                    RISK_OVERDUE,
                    due,
                    f"SN-MERGE|{at}|{due}",
                    now,
                    now,
                ),
            )
        db.conn.commit()

    items = alerts.list_todo_notifications(limit=10)
    assert len(items) == 1
    assert items[0]["shipmentNo"] == "SN-MERGE"
    assert set(items[0]["alertTypes"]) == {"WAREHOUSE_NO_DEPARTURE", "ARRIVAL_NO_DELIVERY"}
    assert len(items[0]["relatedAlertIds"]) == 2
    assert alerts.count_todo() == 1
    assert alerts.summary_counts()["pendingOpen"] == 1


def test_event_key_stable_across_reimport(tmp_path: Path) -> None:
    db, alerts = _prep(tmp_path)
    old_id = str(uuid.uuid4())
    new_id = str(uuid.uuid4())
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, channel_code, warehouse_entry_time,
                created_time, updated_time
            ) VALUES (?, 'SN-RE', 'CH1', '2026-06-01', ?, ?)
            """,
            (new_id, now, now),
        )
        db.conn.commit()

    created = alerts.upsert_alert(
        shipment_id=old_id,
        shipment_no="SN-RE",
        risk_level=RISK_OVERDUE,
        event_key="SN-RE|WAREHOUSE_NO_DEPARTURE|2026-06-01",
        due_date="2026-06-08",
        warning_date="2026-06-08",
        rule_id="",
        rule_scope="",
        channel_code="CH1",
        carrier_code="",
        start_field="warehouse_entry_time",
        start_time="2026-06-01",
        alert_type=ALERT_WAREHOUSE_NO_DEPARTURE,
    )
    assert created is True
    again = alerts.upsert_alert(
        shipment_id=new_id,
        shipment_no="SN-RE",
        risk_level=RISK_OVERDUE,
        event_key="SN-RE|WAREHOUSE_NO_DEPARTURE|2026-06-01",
        due_date="2026-06-08",
        warning_date="2026-06-08",
        rule_id="",
        rule_scope="",
        channel_code="CH1",
        carrier_code="",
        start_field="warehouse_entry_time",
        start_time="2026-06-01",
        alert_type=ALERT_WAREHOUSE_NO_DEPARTURE,
    )
    assert again is False
    open_n = db.conn.execute(
        "SELECT COUNT(*) AS c FROM shipment_sla_alerts WHERE status='open'"
    ).fetchone()["c"]
    assert open_n == 1
    row = db.conn.execute(
        "SELECT shipment_id FROM shipment_sla_alerts WHERE status='open'"
    ).fetchone()
    assert row["shipment_id"] == new_id


def test_list_alerts_todo_keeps_most_severe_per_shipment(tmp_path: Path) -> None:
    db, alerts = _prep(tmp_path)
    now = now_str()
    sid = str(uuid.uuid4())
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, channel_code, created_time, updated_time
            ) VALUES (?, 'SN-ONE', 'CH1', ?, ?)
            """,
            (sid, now, now),
        )
        db.conn.execute(
            """
            INSERT INTO shipment_sla_alerts (
                id, shipment_id, shipment_no, alert_type, risk_level, status, severity,
                due_date, event_key, created_time, updated_time
            ) VALUES
            (?, ?, 'SN-ONE', 'ARRIVAL_NO_DELIVERY', 'overdue', 'open', 'warning',
             '2026-04-24', 'SN-ONE|ARRIVAL|1', ?, ?),
            (?, ?, 'SN-ONE', 'DELIVERY_TIME', 'warning_soon', 'open', 'info',
             '2026-08-06', 'SN-ONE|DELIVERY|1', ?, ?)
            """,
            (
                str(uuid.uuid4()),
                sid,
                now,
                now,
                str(uuid.uuid4()),
                sid,
                now,
                now,
            ),
        )
        db.conn.commit()

    res = alerts.list_alerts(scope="todo", limit=20)
    assert res["total"] == 1
    assert len(res["items"]) == 1
    item = res["items"][0]
    assert item["alertType"] == "ARRIVAL_NO_DELIVERY"
    assert item["riskLevel"] == "overdue"
    assert set(item["alertTypes"]) == {"ARRIVAL_NO_DELIVERY", "DELIVERY_TIME"}
    assert len(item["relatedAlertIds"]) == 2

    # 历史模式仍逐条
    all_res = alerts.list_alerts(scope="all", limit=20)
    assert all_res["total"] == 2
