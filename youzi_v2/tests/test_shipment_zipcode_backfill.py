"""运单邮编回写批处理。"""

from __future__ import annotations

import uuid
from pathlib import Path

from youzi_v2.db.addresses_table import TABLE_NAME as ADDRESSES_TABLE
from youzi_v2.db.addresses_warehouse_table import TABLE_NAME as WAREHOUSE_TABLE
from youzi_v2.db.connection import Database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipment_groups_table import ensure_schema as ensure_group_schema
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.shipments_table import TABLE_NAME as SHIPMENTS_TABLE, ensure_schema as ensure_shipments_schema
from youzi_v2.services.shipment_zipcode_backfill import (
    build_postcode_lookup,
    run_zipcode_backfill_batch,
)


def _seed(db: Database) -> None:
    now = now_str()
    with db.lock:
        db.conn.execute(
            f"""
            INSERT INTO {WAREHOUSE_TABLE} (
                id, warehouse_code, address_type, company, contact, country_code,
                postcode, state, city, address_line1, address_line2, address_line3,
                phone, note1, note2, sort_order, created_at, updated_at
            ) VALUES (?, 'PHX3', 'AMZ', '', '', 'US', '85043', '', '', '', '', '', '', '', '', 0, ?, ?)
            """,
            (str(uuid.uuid4()), now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {ADDRESSES_TABLE} (
                id, customer, product_name, country, address_line, postcode,
                company, contact, phone, is_commercial, is_remote,
                sort_order, is_default, created_at, updated_at
            ) VALUES (?, '00', '00', 'US', '3PL-ADDR-1', '90210', 'Acme', '', '', 1, 0, 0, 0, ?, ?)
            """,
            (str(uuid.uuid4()), now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, address_code, delivery_address, zipcode, created_time, updated_time
            ) VALUES (?, 'SN-ZIP-001', 'PHX3', NULL, NULL, ?, ?)
            """,
            (str(uuid.uuid4()), now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, address_code, delivery_address, zipcode, created_time, updated_time
            ) VALUES (?, 'SN-ZIP-002', NULL, '3PL-ADDR-1', '', ?, ?)
            """,
            (str(uuid.uuid4()), now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, address_code, delivery_address, zipcode, created_time, updated_time
            ) VALUES (?, 'SN-ZIP-003', 'UNKNOWN', NULL, NULL, ?, ?)
            """,
            (str(uuid.uuid4()), now, now),
        )
        db.conn.execute(
            f"""
            INSERT INTO {SHIPMENTS_TABLE} (
                id, shipment_no, address_code, delivery_address, zipcode, created_time, updated_time
            ) VALUES (?, 'SN-ZIP-004', 'HAS-ZIP', NULL, '12345', ?, ?)
            """,
            (str(uuid.uuid4()), now, now),
        )
        db.conn.commit()


def test_zipcode_backfill_from_address_library(tmp_path: Path) -> None:
    db = Database(tmp_path / "zip.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    from youzi_v2.db.addresses_table import ensure_schema as ensure_addresses_schema
    from youzi_v2.db.addresses_warehouse_table import ensure_schema as ensure_wh_schema

    ensure_addresses_schema(db.conn)
    ensure_wh_schema(db.conn)
    _seed(db)

    warehouse, private = build_postcode_lookup(db)
    assert warehouse["PHX3"] == "85043"
    assert private["3PL-ADDR-1"] == "90210"

    repo = ShipmentsRepository(db)
    result = run_zipcode_backfill_batch(repo, force=True, trigger="manual")
    assert result["skipped"] is False
    assert result["total"] == 3
    assert result["updated"] == 2
    assert result["unmatched"] == 1

    rows = {
        r["shipment_no"]: r["zipcode"]
        for r in db.conn.execute(f"SELECT shipment_no, zipcode FROM {SHIPMENTS_TABLE}").fetchall()
    }
    assert rows["SN-ZIP-001"] == "85043"
    assert rows["SN-ZIP-002"] == "90210"
    assert rows["SN-ZIP-003"] in (None, "")
    assert rows["SN-ZIP-004"] == "12345"


def test_list_shipments_no_zipcode_filter(tmp_path: Path) -> None:
    db = Database(tmp_path / "filter.db")
    ensure_shipments_schema(db.conn)
    ensure_group_schema(db.conn)
    from youzi_v2.db.addresses_table import ensure_schema as ensure_addresses_schema
    from youzi_v2.db.addresses_warehouse_table import ensure_schema as ensure_wh_schema

    ensure_addresses_schema(db.conn)
    ensure_wh_schema(db.conn)
    _seed(db)
    repo = ShipmentsRepository(db)

    missing = repo.list_rows(no_zipcode=True, limit=50)
    assert missing["total"] == 3
    nos = {row["shipmentNo"] for row in missing["items"]}
    assert nos == {"SN-ZIP-001", "SN-ZIP-002", "SN-ZIP-003"}

    all_rows = repo.list_rows(limit=50)
    assert all_rows["total"] == 4
