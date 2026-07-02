"""承运商码表保存时，将运单 carrier_code 从中文名归一为编码。"""

from __future__ import annotations

import uuid
from pathlib import Path

from youzi_v2.db.code_tables_repository import CodeTablesRepository
from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_groups_table import ensure_schema as ensure_group_schema
from youzi_v2.db.shipments_table import TABLE_NAME, ensure_schema as ensure_shipments_schema


def _insert_shipment(db: Database, shipment_no: str, carrier_code: str) -> None:
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (id, shipment_no, carrier_code, created_time, updated_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), shipment_no, carrier_code, now, now),
        )
        db.conn.commit()


def test_update_carrier_code_replaces_shipments_by_name_zh(tmp_path: Path) -> None:
    db = Database(tmp_path / "cr.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    code_repo = CodeTablesRepository(db)

    code_repo.insert_row(
        "carrier_codes",
        {
            "code": "UPS",
            "nameZh": "UPS快递",
            "nameEn": "UPS",
            "carrierId": "ups-1",
        },
    )
    _insert_shipment(db, "SN-1", "UPS快递")
    _insert_shipment(db, "SN-2", "UPS")
    _insert_shipment(db, "SN-3", "FedEx联邦")

    updated = code_repo.update_row(
        "carrier_codes",
        "UPS",
        {
            "nameZh": "UPS国际快递",
            "nameEn": "UPS",
            "carrierId": "ups-1",
        },
    )
    assert updated.get("shipmentsCarrierCodeReplaced") == 2

    rows = {
        r["shipment_no"]: r["carrier_code"]
        for r in db.conn.execute(f"SELECT shipment_no, carrier_code FROM {TABLE_NAME}").fetchall()
    }
    assert rows["SN-1"] == "ups-1"
    assert rows["SN-2"] == "ups-1"
    assert rows["SN-3"] == "FedEx联邦"


def test_insert_carrier_code_replaces_shipments_by_name_zh(tmp_path: Path) -> None:
    db = Database(tmp_path / "cr2.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    code_repo = CodeTablesRepository(db)

    _insert_shipment(db, "SN-10", "DHL国际")

    created = code_repo.insert_row(
        "carrier_codes",
        {
            "code": "DHL",
            "nameZh": "DHL国际",
            "nameEn": "DHL",
            "carrierId": "dhl-1",
        },
    )
    assert created.get("shipmentsCarrierCodeReplaced") == 1

    row = db.conn.execute(
        f"SELECT carrier_code FROM {TABLE_NAME} WHERE shipment_no = ?",
        ("SN-10",),
    ).fetchone()
    assert row["carrier_code"] == "dhl-1"
