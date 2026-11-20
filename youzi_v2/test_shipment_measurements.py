"""实重/体积同步与存储回归测试，全部使用虚构数据及内存数据库。"""
import sqlite3
import threading

import pytest

from youzi_v2.db.connection import Database
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.shipments_table import _CREATE_SQL, ensure_schema
from youzi_v2.services.shipment_dps_mapper import dps_row_to_shipment
from youzi_v2.services.shipment_dps_sync_fields import filter_dps_payload, load_dps_sync_fields_config


@pytest.mark.parametrize('status', ['0', '01', '1', '2', '3'])
def test_measurements_roundtrip_and_refresh(status):
    db = Database.__new__(Database)
    db._conn = sqlite3.connect(':memory:')
    db._conn.row_factory = sqlite3.Row
    db._lock = threading.RLock()
    db._bootstrap()
    repo = ShipmentsRepository(db)
    cfg = load_dps_sync_fields_config()
    try:
        remote = {'odd': 'EXAMPLE-MEASURE', 'status': status, 'params': {'roughWeightTotal': '123.45', 'volumeTotal': '1.23456'}}
        payload = dps_row_to_shipment(remote)
        payload['status_code'] = status
        item, created = repo.upsert_by_shipment_no(filter_dps_payload(payload, is_new=True, config=cfg))
        assert created
        assert item['actualWeight'] == 123.45
        assert item['volumeCbm'] == 1.23456
        for invalid in ({}, {'roughWeightTotal': '', 'volumeTotal': 'invalid'}, {'roughWeightTotal': 'NaN', 'volumeTotal': 'Infinity'}, {'roughWeightTotal': -1, 'volumeTotal': -1}):
            payload = dps_row_to_shipment({'odd': remote['odd'], 'params': invalid})
            item, created = repo.upsert_by_shipment_no(filter_dps_payload(payload, is_new=False, config=cfg))
            assert not created
            assert item['actualWeight'] == 123.45 and item['volumeCbm'] == 1.23456
        payload = dps_row_to_shipment({'odd': remote['odd'], 'params': {'roughWeightTotal': 0, 'volumeTotal': '0'}})
        item, _ = repo.upsert_by_shipment_no(filter_dps_payload(payload, is_new=False, config=cfg))
        assert item['actualWeight'] == 0 and item['volumeCbm'] == 0
    finally:
        db.conn.close()


def test_measurements_only_use_params():
    item = dps_row_to_shipment({'odd': 'EXAMPLE', 'roughWeightTotal': 500, 'volumeTotal': 5})
    assert item.get('actual_weight') is None and item.get('volume_cbm') is None


def test_existing_database_migration_is_repeatable():
    conn = sqlite3.connect(':memory:')
    try:
        conn.execute(_CREATE_SQL.replace('    actual_weight REAL,\n', '').replace('    volume_cbm REAL,\n', ''))
        conn.execute("INSERT INTO shipments(id, shipment_no, created_time, updated_time) VALUES ('example', 'EXAMPLE', '', '')")
        ensure_schema(conn)
        ensure_schema(conn)
        assert conn.execute('SELECT actual_weight, volume_cbm FROM shipments').fetchone() == (None, None)
        conn.execute('UPDATE shipments SET actual_weight=20, volume_cbm=0.125')
        ensure_schema(conn)
        assert conn.execute('SELECT actual_weight, volume_cbm FROM shipments').fetchone() == (20, 0.125)
    finally:
        conn.close()
