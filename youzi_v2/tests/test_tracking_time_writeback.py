"""内部轨迹时间字段解析与回写。"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_tracking_time_candidates_repository import (
    ShipmentTrackingTimeCandidatesRepository,
)
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.tracking_logs_repository import TrackingLogsRepository
from youzi_v2.services.tracking_time_writeback import (
    approve_signed_time_candidate,
    recalculate_for_shipment,
)
from youzi_v2.tracking_time_parser import (
    build_time_candidates,
    is_signed_track,
    tracks_from_rows,
)


@pytest.fixture
def env(tmp_path: Path):
    db = Database(tmp_path / "writeback.db")
    shipments = ShipmentsRepository(db)
    tracks = TrackingLogsRepository(db)
    candidates = ShipmentTrackingTimeCandidatesRepository(db)
    return db, shipments, tracks, candidates


def _insert_shipment(shipments: ShipmentsRepository, shipment_no: str = "SH001") -> str:
    sid = str(uuid.uuid4())
    now = now_str()
    with shipments._database.lock:
        shipments._conn.execute(
            """
            INSERT INTO shipments (
                id, shipment_no, status_code, created_time, updated_time,
                tracking_log_count
            ) VALUES (?, ?, 'IN_TRANSIT', ?, ?, 0)
            """,
            (sid, shipment_no, now, now),
        )
        shipments._conn.commit()
    return sid


def _insert_track(
    tracks: TrackingLogsRepository,
    shipment_no: str,
    tracking_time: str,
    tracking_desc: str,
) -> str:
    row = tracks.insert_row(shipment_no, tracking_time, tracking_desc)
    return row["id"]


def test_parse_explicit_voyage_dates() -> None:
    tracks = tracks_from_rows(
        [
            {
                "id": "t1",
                "tracking_time": "2026-05-20 10:00:00",
                "tracking_desc": "LURLINE/100E ETD:5/27 ETA:6/9",
                "created_time": "2026-05-20 10:00:00",
            },
            {
                "id": "t2",
                "tracking_time": "2026-05-25 10:00:00",
                "tracking_desc": "LURLINE/100E ETD:5/28 ETA:6/10",
                "created_time": "2026-05-25 10:00:00",
            },
            {
                "id": "t3",
                "tracking_time": "2026-05-28 10:00:00",
                "tracking_desc": "LURLINE/100E ATD:5/28 ETA:6/10",
                "created_time": "2026-05-28 10:00:00",
            },
        ]
    )
    candidates = build_time_candidates(tracks, shipment_created_time="2026-05-01 08:00:00")
    assert candidates["etd"] is not None
    assert candidates["etd"].candidate_value == "2026-05-28 00:00:00"
    assert candidates["atd"] is not None
    assert candidates["atd"].candidate_value == "2026-05-28 00:00:00"
    assert candidates["eta"] is not None
    assert candidates["eta"].candidate_value == "2026-06-10 00:00:00"


def test_parse_explicit_voyage_dates_with_full_year() -> None:
    tracks = tracks_from_rows(
        [
            {
                "id": "t1",
                "tracking_time": "2026-05-26 12:42:00",
                "tracking_desc": "Loaded ETD:2026/05/28,ETA:2026/06/11",
                "created_time": "2026-05-26 12:42:00",
            },
        ]
    )
    candidates = build_time_candidates(tracks, shipment_created_time="2026-05-01 08:00:00")
    assert candidates["etd"] is not None
    assert candidates["etd"].candidate_value == "2026-05-28 00:00:00"
    assert candidates["eta"] is not None
    assert candidates["eta"].candidate_value == "2026-06-11 00:00:00"


def test_parse_atd_from_goods_shipped_track_when_no_explicit_atd() -> None:
    tracks = tracks_from_rows(
        [
            {
                "id": "t1",
                "tracking_time": "2026-05-18 10:51:00",
                "tracking_desc": (
                    "The goods have been shipped，2026/05/18已开船，"
                    "ETA:2026/06/02,实际到港时间以官网更新为准。"
                ),
                "created_time": "2026-05-18 10:51:00",
            },
            {
                "id": "t2",
                "tracking_time": "2026-05-20 10:00:00",
                "tracking_desc": "LURLINE/100E ETD:5/28 ETA:6/10",
                "created_time": "2026-05-20 10:00:00",
            },
        ]
    )
    candidates = build_time_candidates(tracks, shipment_created_time="2026-05-01 08:00:00")
    assert candidates["atd"] is not None
    assert candidates["atd"].candidate_value == "2026-05-18 10:51:00"
    assert candidates["atd"].source_track_id == "t1"


def test_goods_shipped_does_not_match_waiting_to_be_shipped() -> None:
    from youzi_v2.tracking_time_parser import is_goods_shipped_track

    assert not is_goods_shipped_track(
        "The container has been extracted and is waiting to be shipped to Canada"
    )


def test_parse_ata_from_arrival_node() -> None:
    tracks = tracks_from_rows(
        [
            {
                "id": "t1",
                "tracking_time": "2026-06-09 15:30:00",
                "tracking_desc": "Arriving at the destination, waiting for unloading",
                "created_time": "2026-06-09 15:30:00",
            }
        ]
    )
    candidates = build_time_candidates(tracks)
    assert candidates["ata"] is not None
    assert candidates["ata"].candidate_value == "2026-06-09 15:30:00"


def test_parse_expected_delivery_and_signed_auto_confirm(env) -> None:
    db, shipments, tracks, _ = env
    sid = _insert_shipment(shipments)
    _insert_track(tracks, "SH001", "2026-06-10 09:00:00", "Expected to be delivered on 6/14")
    _insert_track(tracks, "SH001", "2026-06-14 18:00:00", "Your goods have been signed for")

    result = recalculate_for_shipment(db, shipment_id=sid)
    row = shipments.get_by_id(sid)
    assert "expected_delivery_time" in result["applied"]
    assert "signed_time" in result["applied"]
    assert row["expectedDeliveryTime"] == "2026-06-14 00:00:00"
    assert row["deliveredTime"] == "2026-06-14 00:00:00"
    assert row["statusCode"] == "IN_TRANSIT"


def test_signed_conflict_pending_review(env) -> None:
    db, shipments, tracks, candidates_repo = env
    sid = _insert_shipment(shipments)
    _insert_track(tracks, "SH001", "2026-06-10 09:00:00", "Expected to be delivered on 6/15")
    _insert_track(tracks, "SH001", "2026-06-28 18:00:00", "Your goods have been signed for")

    result = recalculate_for_shipment(db, shipment_id=sid)
    row = shipments.get_by_id(sid)
    assert result["pendingReview"] == ["signed_time"]
    assert row["expectedDeliveryTime"] == "2026-06-15 00:00:00"
    assert not row.get("deliveredTime")
    assert row["statusCode"] == "IN_TRANSIT"

    pending = candidates_repo.list_for_shipment(sid)
    signed = next(item for item in pending if item["fieldName"] == "signed_time")
    assert signed["reviewStatus"] == "pending_review"
    assert signed["candidateValue"] == "2026-06-15 00:00:00"
    assert signed["compareValue"] == "2026-06-28 18:00:00"
    assert signed["recommendedSource"] == "expected_delivery_time"
    assert signed["compareSource"] == "signed_track_time"
    assert "需确认是否采用预计送仓时间" in signed["reviewReason"]


def test_manual_approve_use_expected_delivery(env) -> None:
    db, shipments, tracks, candidates_repo = env
    sid = _insert_shipment(shipments)
    _insert_track(tracks, "SH001", "2026-06-10 09:00:00", "Expected to be delivered on 6/15")
    _insert_track(tracks, "SH001", "2026-06-28 18:00:00", "Your goods have been signed for")
    recalculate_for_shipment(db, shipment_id=sid)
    signed = next(
        item
        for item in candidates_repo.list_for_shipment(sid)
        if item["fieldName"] == "signed_time"
    )
    approve_signed_time_candidate(db, signed["id"], action="use_expected_delivery")
    row = shipments.get_by_id(sid)
    assert row["deliveredTime"] == "2026-06-15 00:00:00"
    assert row["statusCode"] == "IN_TRANSIT"


def test_manual_approve_use_signed_track(env) -> None:
    db, shipments, tracks, candidates_repo = env
    sid = _insert_shipment(shipments)
    _insert_track(tracks, "SH001", "2026-06-10 09:00:00", "Expected to be delivered on 6/15")
    _insert_track(tracks, "SH001", "2026-06-28 18:00:00", "Your goods have been signed for")
    recalculate_for_shipment(db, shipment_id=sid)
    signed = next(
        item
        for item in candidates_repo.list_for_shipment(sid)
        if item["fieldName"] == "signed_time"
    )
    approve_signed_time_candidate(db, signed["id"], action="use_signed_track")
    row = shipments.get_by_id(sid)
    assert row["deliveredTime"] == "2026-06-28 18:00:00"


def test_parse_warehouse_entry_from_in_warehouse_node() -> None:
    from youzi_v2.internal_tracking import INTERNAL_WAREHOUSE_PLACEHOLDER

    tracks = tracks_from_rows(
        [
            {
                "id": "t1",
                "tracking_time": "2026-05-18 14:20:00",
                "tracking_desc": INTERNAL_WAREHOUSE_PLACEHOLDER,
                "created_time": "2026-05-19 09:00:00",
            },
            {
                "id": "t2",
                "tracking_time": "2026-05-20 10:00:00",
                "tracking_desc": INTERNAL_WAREHOUSE_PLACEHOLDER,
                "created_time": "2026-05-20 10:00:00",
            },
        ]
    )
    candidates = build_time_candidates(tracks)
    assert candidates["warehouse_entry_time"] is not None
    assert candidates["warehouse_entry_time"].candidate_value == "2026-05-18 14:20:00"


def test_writeback_warehouse_entry_time(env) -> None:
    from youzi_v2.internal_tracking import INTERNAL_WAREHOUSE_PLACEHOLDER

    db, shipments, tracks, _ = env
    sid = _insert_shipment(shipments)
    _insert_track(tracks, "SH001", "2026-05-18 14:20:00", INTERNAL_WAREHOUSE_PLACEHOLDER)
    _insert_track(tracks, "SH001", "2026-05-28 10:00:00", "LURLINE/100E ATD:5/28 ETA:6/10")

    result = recalculate_for_shipment(db, shipment_id=sid)
    row = shipments.get_by_id(sid)
    assert "warehouse_entry_time" in result["applied"]
    assert row["warehouseEntryTime"] == "2026-05-18 14:20:00"
    assert row["atd"] == "2026-05-28 00:00:00"


def test_delivered_node_case_sensitive() -> None:
    assert is_signed_track("Delivered to Amazon FC")
    assert not is_signed_track("goods delivered to Amazon FC")


def test_delivered_goods_unpacking_not_signed() -> None:
    assert not is_signed_track("Delivered goods, waiting for unpacking")
    assert not is_signed_track(
        "Delivered goods, waiting for unpacking（货物已送达，等待拆箱）",
    )


def test_cross_year_eta(env) -> None:
    db, shipments, tracks, _ = env
    sid = _insert_shipment(shipments)
    _insert_track(tracks, "SH001", "2026-12-28 10:00:00", "LURLINE ETA:1/5")
    recalculate_for_shipment(db, shipment_id=sid)
    row = shipments.get_by_id(sid)
    assert row["eta"] == "2027-01-05 00:00:00"
