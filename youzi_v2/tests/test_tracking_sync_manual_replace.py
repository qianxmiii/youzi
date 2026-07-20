"""手动内部轨迹同步：以接口全量覆盖本地。"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.internal_tracking_logs_table import ensure_schema as ensure_logs_schema
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE, ensure_schema as ensure_shipments_schema
from youzi_v2.db.tracking_logs_repository import TrackingLogsRepository
from youzi_v2.services.tracking_sync import sync_all_tracking


def _seed_shipment(db: Database, shipment_no: str) -> None:
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, status_code, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), shipment_no, "IN_TRANSIT", now, now),
        )
        db.conn.commit()


def test_manual_sync_replaces_stale_local_logs(tmp_path: Path) -> None:
    db = Database(tmp_path / "manual_replace.db")
    ensure_shipments_schema(db.conn)
    ensure_logs_schema(db.conn)
    sn = "SN-MANUAL-1"
    _seed_shipment(db, sn)

    logs_repo = TrackingLogsRepository(db)
    logs_repo.insert_row(sn, "2026-07-07 14:45:54", "Ghost node removed in DPS")
    logs_repo.insert_row(sn, "2026-07-06 14:54:25", "Your goods have been signed for")

    api_item = {
        "odd": sn,
        "status": "3",
        "logisticsInfors": [
            {
                "nodeTime": "2026-07-06 14:54:25",
                "nodeDesc": "Your goods have been signed for（已签收）",
            },
        ],
    }

    with (
        patch(
            "youzi_v2.services.tracking_sync.load_logistics_config",
            return_value={"base_url": "http://test.local"},
        ),
        patch(
            "youzi_v2.services.tracking_sync.query_logistics_api",
            return_value=([api_item], []),
        ),
        patch(
            "youzi_v2.services.tracking_sync.evaluate_groups_after_tracking_sync",
            return_value={},
        ),
        patch(
            "youzi_v2.services.tracking_sync.evaluate_sla_after_tracking_sync",
            return_value={},
        ),
        patch(
            "youzi_v2.services.tracking_sync.recalculate_for_shipment_nos",
            return_value={"processed": 0, "appliedTotal": 0, "pendingReviewTotal": 0},
        ),
    ):
        result = sync_all_tracking(
            ShipmentsRepository(db),
            logs_repo,
            tmp_path / "config.json",
            shipment_nos=[sn],
            trigger="manual",
        )

    assert result["updated"] == 1
    rows = db.conn.execute(
        "SELECT tracking_time, tracking_desc FROM internal_tracking_logs WHERE shipment_no = ? ORDER BY tracking_time",
        (sn,),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["tracking_time"] == "2026-07-06 14:54:25"
    assert "Ghost" not in (rows[0]["tracking_desc"] or "")


def test_manual_sync_dedupes_duplicate_api_nodes(tmp_path: Path) -> None:
    db = Database(tmp_path / "manual_dedupe.db")
    ensure_shipments_schema(db.conn)
    ensure_logs_schema(db.conn)
    sn = "SN-DEDUP-1"
    _seed_shipment(db, sn)
    logs_repo = TrackingLogsRepository(db)

    api_item = {
        "odd": sn,
        "status": "2",
        "logisticsInfors": [
            {"nodeTime": "2026-07-15 10:00:00", "nodeDesc": "Same node twice"},
            {"nodeTime": "2026-07-15 10:00:00", "nodeDesc": "Same node twice"},
            {"nodeTime": "2026-07-14 09:00:00", "nodeDesc": "Earlier node"},
        ],
    }

    with (
        patch(
            "youzi_v2.services.tracking_sync.load_logistics_config",
            return_value={"base_url": "http://test.local"},
        ),
        patch(
            "youzi_v2.services.tracking_sync.query_logistics_api",
            return_value=([api_item], []),
        ),
        patch(
            "youzi_v2.services.tracking_sync.evaluate_groups_after_tracking_sync",
            return_value={},
        ),
        patch(
            "youzi_v2.services.tracking_sync.evaluate_sla_after_tracking_sync",
            return_value={},
        ),
        patch(
            "youzi_v2.services.tracking_sync.recalculate_for_shipment_nos",
            return_value={"processed": 0, "appliedTotal": 0, "pendingReviewTotal": 0},
        ),
    ):
        result = sync_all_tracking(
            ShipmentsRepository(db),
            logs_repo,
            tmp_path / "config.json",
            shipment_nos=[sn],
            trigger="manual",
        )

    assert result["updated"] == 1
    assert result["logCount"] == 2
    rows = db.conn.execute(
        "SELECT tracking_time, tracking_desc FROM internal_tracking_logs WHERE shipment_no = ?",
        (sn,),
    ).fetchall()
    assert len(rows) == 2


def test_scheduled_sync_keeps_stale_local_logs(tmp_path: Path) -> None:
    db = Database(tmp_path / "scheduled_merge.db")
    ensure_shipments_schema(db.conn)
    ensure_logs_schema(db.conn)
    sn = "SN-SCHED-1"
    _seed_shipment(db, sn)

    logs_repo = TrackingLogsRepository(db)
    logs_repo.insert_row(sn, "2026-07-07 14:45:54", "Ghost node kept on scheduled sync")

    api_item = {
        "odd": sn,
        "status": "2",
        "logisticsInfors": [
            {
                "nodeTime": "2026-07-06 14:54:25",
                "nodeDesc": "Your goods have been signed for",
            },
        ],
    }

    with (
        patch(
            "youzi_v2.services.tracking_sync.load_logistics_config",
            return_value={"base_url": "http://test.local"},
        ),
        patch(
            "youzi_v2.services.tracking_sync.query_logistics_api",
            return_value=([api_item], []),
        ),
        patch(
            "youzi_v2.services.tracking_sync.evaluate_groups_after_tracking_sync",
            return_value={},
        ),
        patch(
            "youzi_v2.services.tracking_sync.evaluate_sla_after_tracking_sync",
            return_value={},
        ),
        patch(
            "youzi_v2.services.tracking_sync.recalculate_for_shipment_nos",
            return_value={"processed": 0, "appliedTotal": 0, "pendingReviewTotal": 0},
        ),
        patch(
            "youzi_v2.services.tracking_sync.should_run_scheduled_internal_batch",
            return_value=(True, ""),
        ),
        patch(
            "youzi_v2.services.tracking_sync.record_internal_batch_finished",
            return_value=None,
        ),
    ):
        sync_all_tracking(
            ShipmentsRepository(db),
            logs_repo,
            tmp_path / "config.json",
            shipment_nos=None,
            trigger="scheduled",
        )

    rows = db.conn.execute(
        "SELECT tracking_desc FROM internal_tracking_logs WHERE shipment_no = ? ORDER BY tracking_time",
        (sn,),
    ).fetchall()
    assert len(rows) == 2
    assert any("Ghost" in (r["tracking_desc"] or "") for r in rows)
