"""运单轨迹订阅测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from youzi_v2.db.connection import Database
from youzi_v2.db.shipment_subscriptions_table import ShipmentSubscriptionsRepository
from youzi_v2.db.shipments_repository import ShipmentsRepository


@pytest.fixture
def repos(tmp_path: Path) -> tuple[ShipmentsRepository, ShipmentSubscriptionsRepository]:
    db = Database(tmp_path / "test.db")
    return ShipmentsRepository(db), ShipmentSubscriptionsRepository(db)


def test_subscribe_and_notify_on_internal_tracking_change(
    repos: tuple[ShipmentsRepository, ShipmentSubscriptionsRepository],
) -> None:
    shipments, subs = repos
    with shipments._database.lock:
        shipments._conn.execute(
            """
            INSERT INTO shipments (
                id, shipment_no, status_code, created_time, updated_time,
                latest_tracking_time, latest_tracking_desc, tracking_log_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "sid-1",
                "SH001",
                "IN_TRANSIT",
                "2026-06-01 08:00:00",
                "2026-06-01 08:00:00",
                "2026-06-01 08:00:00",
                "旧节点",
                1,
            ),
        )
        shipments._conn.commit()

    subs.subscribe("sid-1")
    shipments.update_internal_tracking_summary(
        "SH001",
        "2026-06-02 10:00:00",
        "新节点",
        log_count=2,
    )

    notes = subs.list_unread_notifications()
    assert len(notes) == 1
    assert notes[0]["shipmentNo"] == "SH001"
    assert notes[0]["trackingSource"] == "internal"
    assert notes[0]["latestTime"] == "2026-06-02 10:00:00"
    assert notes[0]["latestDesc"] == "新节点"


def test_batch_subscribe(repos: tuple[ShipmentsRepository, ShipmentSubscriptionsRepository]) -> None:
    shipments, subs = repos
    for i, sn in enumerate(("SH001", "SH002"), start=1):
        with shipments._database.lock:
            shipments._conn.execute(
                """
                INSERT INTO shipments (
                    id, shipment_no, status_code, created_time, updated_time
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (f"sid-{i}", sn, "IN_TRANSIT", "2026-06-01 08:00:00", "2026-06-01 08:00:00"),
            )
            shipments._conn.commit()
    result = subs.subscribe_many(["sid-1", "sid-2", "missing"])
    assert result["subscribed"] == 2
    assert result["failed"] == 1
    assert subs.subscribed_shipment_ids() == {"sid-1", "sid-2"}
