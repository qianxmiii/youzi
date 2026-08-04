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


def test_eta_reminder_daily_window(
    repos: tuple[ShipmentsRepository, ShipmentSubscriptionsRepository],
) -> None:
    from datetime import date

    from youzi_v2.db.shipment_subscriptions_table import format_eta_reminder_desc

    shipments, subs = repos
    with shipments._database.lock:
        shipments._conn.execute(
            """
            INSERT INTO shipments (
                id, shipment_no, status_code, eta, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "sid-eta",
                "SH-ETA",
                "IN_TRANSIT",
                "2026-08-10 12:00:00",
                "2026-08-01 08:00:00",
                "2026-08-01 08:00:00",
            ),
        )
        shipments._conn.commit()
    subs.subscribe("sid-eta")

    # ETA-8：尚未进入窗口
    r0 = subs.evaluate_eta_reminders(today=date(2026, 8, 2))
    assert r0["created"] == 0

    # ETA-7：开始提醒
    r1 = subs.evaluate_eta_reminders(today=date(2026, 8, 3))
    assert r1["created"] == 1
    notes = subs.list_unread_notifications()
    assert len(notes) == 1
    assert notes[0]["trackingSource"] == "eta_reminder"
    assert "7 天后到港" in notes[0]["latestDesc"]

    # 同日再次扫描不重复
    r1b = subs.evaluate_eta_reminders(today=date(2026, 8, 3))
    assert r1b["created"] == 0

    # 次日再提醒
    r2 = subs.evaluate_eta_reminders(today=date(2026, 8, 4))
    assert r2["created"] == 1
    assert len(subs.list_unread_notifications()) == 2

    # 签收后停止
    with shipments._database.lock:
        shipments._conn.execute(
            "UPDATE shipments SET status_code = ?, delivered_time = ? WHERE id = ?",
            ("DELIVERED", "2026-08-05 10:00:00", "sid-eta"),
        )
        shipments._conn.commit()
    r3 = subs.evaluate_eta_reminders(today=date(2026, 8, 5))
    assert r3["created"] == 0


def test_format_eta_reminder_desc() -> None:
    from datetime import date

    from youzi_v2.db.shipment_subscriptions_table import format_eta_reminder_desc

    assert "3 天后" in format_eta_reminder_desc(date(2026, 8, 8), date(2026, 8, 5))
    assert "今日预计到港" in format_eta_reminder_desc(date(2026, 8, 5), date(2026, 8, 5))
    assert "已过 ETA 2 天" in format_eta_reminder_desc(date(2026, 8, 3), date(2026, 8, 5))
