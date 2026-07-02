"""渠道码表保存时，将运单 channel_code 从中文名归一为编码。"""

from __future__ import annotations

import uuid
from pathlib import Path

from youzi_v2.db.code_tables_repository import CodeTablesRepository
from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_groups_table import ensure_schema as ensure_group_schema
from youzi_v2.db.shipments_table import TABLE_NAME, ensure_schema as ensure_shipments_schema


def _insert_shipment(db: Database, shipment_no: str, channel_code: str) -> None:
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (id, shipment_no, channel_code, created_time, updated_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), shipment_no, channel_code, now, now),
        )
        db.conn.commit()


def test_update_channel_code_replaces_shipments_by_name_zh(tmp_path: Path) -> None:
    db = Database(tmp_path / "ch.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    code_repo = CodeTablesRepository(db)

    code_repo.insert_row(
        "channel_codes",
        {
            "code": "AEE",
            "nameZh": "空运经济",
            "nameEn": "AEE",
            "country": "US",
            "category": "空运",
        },
    )
    _insert_shipment(db, "SN-1", "空运经济")
    _insert_shipment(db, "SN-2", "AEE")
    _insert_shipment(db, "SN-3", "海运普船")

    updated = code_repo.update_row(
        "channel_codes",
        "AEE",
        {
            "nameZh": "空运经济线",
            "nameEn": "AEE",
            "country": "US",
            "category": "空运",
        },
    )
    assert updated.get("shipmentsChannelCodeReplaced") == 1

    rows = {
        r["shipment_no"]: r["channel_code"]
        for r in db.conn.execute(f"SELECT shipment_no, channel_code FROM {TABLE_NAME}").fetchall()
    }
    assert rows["SN-1"] == "AEE"
    assert rows["SN-2"] == "AEE"
    assert rows["SN-3"] == "海运普船"


def test_insert_channel_code_replaces_shipments_by_name_zh(tmp_path: Path) -> None:
    db = Database(tmp_path / "ch2.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    code_repo = CodeTablesRepository(db)

    _insert_shipment(db, "SN-10", "海运快船")

    created = code_repo.insert_row(
        "channel_codes",
        {
            "code": "SEA-FAST",
            "nameZh": "海运快船",
            "nameEn": "SEA-FAST",
            "country": "US",
            "category": "普船",
        },
    )
    assert created.get("shipmentsChannelCodeReplaced") == 1

    row = db.conn.execute(
        f"SELECT channel_code FROM {TABLE_NAME} WHERE shipment_no = ?",
        ("SN-10",),
    ).fetchone()
    assert row["channel_code"] == "SEA-FAST"
