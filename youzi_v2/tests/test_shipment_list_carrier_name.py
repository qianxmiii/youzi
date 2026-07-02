"""运单列表承运商中文名（关联 carrier_codes 码表）。"""

from __future__ import annotations

import uuid
from pathlib import Path

from youzi_v2.db.code_tables_repository import CodeTablesRepository
from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_groups_table import ensure_schema as ensure_group_schema
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.shipments_table import ensure_schema as ensure_shipments_schema


def test_list_includes_carrier_name_zh_by_code(tmp_path: Path) -> None:
    db = Database(tmp_path / "carrier_name.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    code_repo = CodeTablesRepository(db)
    ship_repo = ShipmentsRepository(db)

    code_repo.insert_row(
        "carrier_codes",
        {"code": "TXFBA", "nameZh": "天图FBA", "carrier_id": "1724258253196189697"},
    )
    now = now_str()
    with db.lock:
        db.conn.execute(
            """
            INSERT INTO shipments (
                id, shipment_no, carrier_code, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-CAR-001", "TXFBA", now, now),
        )
        db.conn.commit()

    items = ship_repo.list_rows(limit=10)["items"]
    assert len(items) == 1
    assert items[0]["carrierCode"] == "TXFBA"
    assert items[0]["carrierNameZh"] == "天图FBA"


def test_list_includes_carrier_name_zh_by_dps_carrier_id(tmp_path: Path) -> None:
    db = Database(tmp_path / "carrier_id.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    code_repo = CodeTablesRepository(db)
    ship_repo = ShipmentsRepository(db)

    code_repo.insert_row(
        "carrier_codes",
        {"code": "MY-CARRIER", "nameZh": "测试承运商", "carrier_id": "1724258253196189697"},
    )
    now = now_str()
    with db.lock:
        db.conn.execute(
            """
            INSERT INTO shipments (
                id, shipment_no, carrier_code, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-CAR-002", "1724258253196189697", now, now),
        )
        db.conn.commit()

    items = ship_repo.list_rows(limit=10)["items"]
    assert len(items) == 1
    assert items[0]["carrierCode"] == "1724258253196189697"
    assert items[0]["carrierNameZh"] == "测试承运商"


def test_filter_options_carriers_include_name_zh(tmp_path: Path) -> None:
    db = Database(tmp_path / "carrier_filter.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    code_repo = CodeTablesRepository(db)
    ship_repo = ShipmentsRepository(db)

    code_repo.insert_row(
        "carrier_codes",
        {"code": "MY-CARRIER", "nameZh": "测试承运商", "carrier_id": "1724258253196189697"},
    )
    now = now_str()
    with db.lock:
        db.conn.execute(
            """
            INSERT INTO shipments (
                id, shipment_no, carrier_code, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), "SN-F-1", "1724258253196189697", now, now),
        )
        db.conn.commit()

    opts = ship_repo.list_filter_options()
    assert len(opts["carriers"]) == 1
    assert opts["carriers"][0]["code"] == "1724258253196189697"
    assert opts["carriers"][0]["nameZh"] == "测试承运商"
    assert opts["carrierCodes"] == ["1724258253196189697"]
