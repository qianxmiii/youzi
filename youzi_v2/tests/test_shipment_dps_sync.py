"""DPS 运单行映射与同步。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from youzi_v2.db.code_tables_repository import CodeTablesRepository
from youzi_v2.db.connection import Database
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.services.shipment_dps_mapper import (
    dps_row_to_shipment,
    map_dps_address_type,
    map_dps_payment_status,
    map_dps_status,
)
from youzi_v2.services.shipment_dps_sync_fields import (
    filter_dps_payload,
    load_dps_sync_fields_config,
)
from youzi_v2.services.shipment_dps_sync import run_shipment_dps_sync_batch

SAMPLE_DELIVERED = {
    "id": "2069113725203427329",
    "odd": "DPSECO260610178",
    "clientUserNickName": "422GS",
    "assOrderNumber": "SP-GS260601-AMZ-US-Air",
    "channelCode": "AEE",
    "deliveryAddressType": "0",
    "deliveryWarehouseCode": "MCI4",
    "deliveryZip": "64163",
    "totalCtns": 2,
    "receiveWarehouseName": "义乌仓",
    "shipperCompanyName": "422-Qingzheng",
    "endCarrier": "UPS",
    "carrierId": "1724258253196189697",
    "endOrderNumber": "1Z9X02R50392023824",
    "signingTime": "2026-06-29 19:53:46",
    "internalOrderNum": "FBA19FN8FN6C",
    "params": {
        "amazonID": "FBA19FN8FN6C",
        "amazonReferenceID": "41HER1CX",
        "countryVo": {"enAbbreviation": "US"},
        "commerceWaybillRouteInfo": {
            "nodeTime": "2026-06-29 19:53:46",
            "nodeDesc": "Your goods have been signed for",
            "status": "601",
            "estimatedDeliveryDate": "2026-06-25 12:54:48",
        },
        "markVos": [{"name": "转运中"}],
    },
}


class ShipmentDpsMapperTest(unittest.TestCase):
    def test_map_delivered_row(self) -> None:
        payload = dps_row_to_shipment(SAMPLE_DELIVERED)
        assert payload is not None
        self.assertEqual(payload["shipment_no"], "DPSECO260610178")
        self.assertEqual(payload["waybill_id"], "2069113725203427329")
        self.assertEqual(payload["customer_no"], "SP-GS260601-AMZ-US-Air")
        self.assertEqual(payload["customer"], "422GS")
        self.assertEqual(payload["country_code"], "US")
        self.assertEqual(payload["status_code"], "DELIVERED")
        self.assertEqual(payload["zipcode"], "64163")
        self.assertEqual(payload["address_type"], "AMZ")
        self.assertNotIn("carrier_id", payload)
        self.assertEqual(payload.get("carrier_code"), "1724258253196189697")

    def test_map_bill_of_lading_no_from_params(self) -> None:
        row = {
            **SAMPLE_DELIVERED,
            "params": {
                **SAMPLE_DELIVERED["params"],
                "ladingBillNum": "OOLU2169890590",
            },
        }
        payload = dps_row_to_shipment(row)
        assert payload is not None
        self.assertEqual(payload.get("bill_of_lading_no"), "OOLU2169890590")

    def test_map_carrier_code_uses_carrier_id_only(self) -> None:
        payload = dps_row_to_shipment(SAMPLE_DELIVERED)
        assert payload is not None
        self.assertEqual(payload.get("carrier_code"), "1724258253196189697")
        row = {
            **SAMPLE_DELIVERED,
            "carrierId": "999",
            "endCarrier": "FedEx",
            "carrierName": "UPS",
        }
        payload2 = dps_row_to_shipment(row)
        assert payload2 is not None
        self.assertEqual(payload2.get("carrier_code"), "999")

    def test_map_address_type_private(self) -> None:
        row = {**SAMPLE_DELIVERED, "deliveryAddressType": "2"}
        payload = dps_row_to_shipment(row)
        assert payload is not None
        self.assertEqual(payload["address_type"], "3PL")

    def test_map_payment_status(self) -> None:
        self.assertEqual(map_dps_payment_status(0), "UNPAID")
        self.assertEqual(map_dps_payment_status(1), "PAID")
        self.assertEqual(map_dps_payment_status("0"), "UNPAID")
        self.assertEqual(map_dps_payment_status("1"), "PAID")
        self.assertIsNone(map_dps_payment_status(None))
        self.assertIsNone(map_dps_payment_status(""))

    def test_map_payment_status_from_row(self) -> None:
        unpaid = dps_row_to_shipment({**SAMPLE_DELIVERED, "clientVerifyStatus": 0})
        paid = dps_row_to_shipment({**SAMPLE_DELIVERED, "clientVerifyStatus": 1})
        assert unpaid is not None and paid is not None
        self.assertEqual(unpaid["payment_status"], "UNPAID")
        self.assertEqual(paid["payment_status"], "PAID")

    def test_map_address_type_wfs(self) -> None:
        row = {
            **SAMPLE_DELIVERED,
            "deliveryAddressType": "0",
            "deliveryWarehouseCode": "WFS-US-01",
        }
        payload = dps_row_to_shipment(row)
        assert payload is not None
        self.assertEqual(payload["address_type"], "WFS")

    def test_customer_no_falls_back_to_internal_order_num(self) -> None:
        row = {**SAMPLE_DELIVERED}
        row.pop("assOrderNumber", None)
        row["internalOrderNum"] = "MFDPS88"
        payload = dps_row_to_shipment(row)
        assert payload is not None
        self.assertEqual(payload["customer_no"], "MFDPS88")
        self.assertEqual(payload["customer_shipment_id"], "FBA19FN8FN6C")

    def test_customer_no_prefers_ass_order_number(self) -> None:
        row = {
            **SAMPLE_DELIVERED,
            "assOrderNumber": "CUST-PO-001",
            "internalOrderNum": "MFDPS88",
        }
        payload = dps_row_to_shipment(row)
        assert payload is not None
        self.assertEqual(payload["customer_no"], "CUST-PO-001")

    def test_customer_no_empty_when_both_missing(self) -> None:
        row = {**SAMPLE_DELIVERED}
        row.pop("assOrderNumber", None)
        row.pop("internalOrderNum", None)
        payload = dps_row_to_shipment(row)
        assert payload is not None
        self.assertEqual(payload["customer_no"], "")

    def test_customer_shipment_id_skips_internal_order_num(self) -> None:
        row = {
            **SAMPLE_DELIVERED,
            "internalOrderNum": "FBA19FN8FN6C",
            "params": {**SAMPLE_DELIVERED["params"], "amazonID": ""},
        }
        payload = dps_row_to_shipment(row)
        assert payload is not None
        self.assertNotIn("customer_shipment_id", payload)
        # amazonID 空时 internalOrderNum 只回填客户单号，不写入货件号
        self.assertEqual(payload["customer_no"], "SP-GS260601-AMZ-US-Air")

    def test_map_address_type_direct(self) -> None:
        self.assertEqual(map_dps_address_type("0"), "AMZ")
        self.assertEqual(map_dps_address_type("2"), "3PL")
        self.assertEqual(
            map_dps_address_type("0", address_code="WFS123"),
            "WFS",
        )

    def test_map_in_transit_from_marks(self) -> None:
        row = {
            **SAMPLE_DELIVERED,
            "signingTime": None,
            "params": {
                **SAMPLE_DELIVERED["params"],
                "commerceWaybillRouteInfo": {
                    "nodeTime": "2026-06-13 12:10:21",
                    "nodeDesc": "in transit",
                    "status": "202",
                },
            },
        }
        status = map_dps_status(
            row,
            row["params"]["commerceWaybillRouteInfo"],
            row["params"],
        )
        self.assertEqual(status, "IN_TRANSIT")


class ShipmentDpsSyncFieldsTest(unittest.TestCase):
    def test_filter_update_skips_status_and_tracking(self) -> None:
        cfg_path = Path(__file__).resolve().parents[1] / "config" / "shipment_dps_sync_fields.json"
        cfg = load_dps_sync_fields_config(cfg_path)
        payload = {
            "shipment_no": "A",
            "customer": "c1",
            "status_code": "DELIVERED",
            "latest_tracking_time": "2026-01-01 00:00:00",
            "latest_tracking_desc": "signed",
        }
        on_update = filter_dps_payload(payload, is_new=False, config=cfg)
        self.assertEqual(on_update["shipment_no"], "A")
        self.assertEqual(on_update["customer"], "c1")
        self.assertNotIn("status_code", on_update)
        self.assertNotIn("latest_tracking_time", on_update)
        self.assertNotIn("latest_tracking_desc", on_update)

        on_insert = filter_dps_payload(payload, is_new=True, config=cfg)
        self.assertIn("status_code", on_insert)


class ShipmentDpsSyncTest(unittest.TestCase):
    def test_sync_upserts_rows(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        repo = ShipmentsRepository(db)
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "shipment_queryByPerson": {
                        "url": "https://example.com/list?pageSize=10",
                        "Authorization": "token",
                    }
                }
            ),
            encoding="utf-8",
        )

        fake_result = {
            "code": 200,
            "msg": "ok",
            "total": 1,
            "rows": [SAMPLE_DELIVERED],
            "pages": 1,
            "transitTimeStart": "2026-06-01 00:00:00",
            "transitTimeEnd": "2026-06-30 23:59:59",
        }

        with patch(
            "youzi_v2.services.shipment_dps_sync.query_shipments_by_person",
            return_value=(fake_result, None),
        ):
            result = run_shipment_dps_sync_batch(
                repo,
                cfg_path,
                force=True,
                trigger="manual",
            )

        self.assertFalse(result["skipped"])
        self.assertEqual(result["created"], 1)
        row = repo.get_by_shipment_no("DPSECO260610178")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["customer"], "422GS")
        self.assertEqual(row["carrierCode"], "1724258253196189697")
        self.assertEqual(row["waybillId"], "2069113725203427329")
        self.assertFalse(row.get("carrierId"))
        db.conn.close()
        tmp.cleanup()

    def test_sync_carrier_id_stores_dps_carrier_id_in_carrier_code(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        repo = ShipmentsRepository(db)
        code_repo = CodeTablesRepository(db)
        code_repo.insert_row(
            "carrier_codes",
            {"code": "MY-CARRIER", "nameZh": "测试承运商", "carrier_id": "1724258253196189697"},
        )
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "shipment_queryByPerson": {
                        "url": "https://example.com/list?pageSize=10",
                        "Authorization": "token",
                    }
                }
            ),
            encoding="utf-8",
        )
        row = {**SAMPLE_DELIVERED, "endCarrier": None, "carrierName": None}
        fake_result = {
            "code": 200,
            "msg": "ok",
            "total": 1,
            "rows": [row],
            "pages": 1,
        }
        with patch(
            "youzi_v2.services.shipment_dps_sync.query_shipments_by_person",
            return_value=(fake_result, None),
        ):
            run_shipment_dps_sync_batch(repo, cfg_path, force=True, trigger="manual")
        saved = repo.get_by_shipment_no("DPSECO260610178")
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved["carrierCode"], "1724258253196189697")
        self.assertFalse(saved.get("carrierId"))
        db.conn.close()
        tmp.cleanup()

    def test_sync_by_order_upserts_selected(self) -> None:
        from youzi_v2.services.shipment_dps_sync import run_shipment_dps_sync_by_order

        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        repo = ShipmentsRepository(db)
        cfg_path = Path(tmp.name) / "config.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "shipment_queryByOrder": {
                        "url": "https://example.com/list?pageSize=10",
                        "Authorization": "token",
                    }
                }
            ),
            encoding="utf-8",
        )
        fake_result = {
            "code": 200,
            "msg": "ok",
            "total": 1,
            "rows": [SAMPLE_DELIVERED],
            "pages": 1,
        }
        captured: list[tuple[Any, Any]] = []

        def fake_query(shipment_nos, config_path, timeout=30):
            captured.append((shipment_nos, config_path))
            return fake_result, None

        with patch(
            "youzi_v2.services.shipment_dps_sync.query_shipments_by_order",
            fake_query,
        ):
            result = run_shipment_dps_sync_by_order(
                repo,
                cfg_path,
                ["DPSECO260610178", "MISSING-NO"],
            )
        self.assertFalse(result["skipped"])
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["notFound"], 1)
        self.assertIn("MISSING-NO", result["notFoundNos"])
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], ["DPSECO260610178", "MISSING-NO"])
        self.assertTrue(captured[0][1].is_file())
        row = repo.get_by_shipment_no("DPSECO260610178")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["waybillId"], "2069113725203427329")
        db.conn.close()
        tmp.cleanup()

    def test_sync_backfills_payment_status_when_local_empty(self) -> None:
        from youzi_v2.services.shipment_dps_sync import _upsert_dps_rows

        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        repo = ShipmentsRepository(db)
        now = "2026-05-17 23:31:55"
        repo.insert_row(
            {
                "shipment_no": "DPSECO260327063",
                "customer": "老客户",
                "created_time": now,
                "updated_time": now,
            }
        )
        row = repo.get_by_shipment_no("DPSECO260327063")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertIsNone(row.get("paymentStatus"))

        dps_row = {**SAMPLE_DELIVERED, "odd": "DPSECO260327063", "clientVerifyStatus": 0}
        stats = _upsert_dps_rows(repo, [dps_row])
        self.assertEqual(stats["failed"], 0)

        saved = repo.get_by_shipment_no("DPSECO260327063")
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved["paymentStatus"], "UNPAID")
        self.assertEqual(saved["customer"], "422GS")
        db.conn.close()
        tmp.cleanup()

    def test_sync_does_not_overwrite_paid_payment_status(self) -> None:
        from youzi_v2.services.shipment_dps_sync import _upsert_dps_rows

        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        repo = ShipmentsRepository(db)
        now = "2026-07-11 12:00:00"
        repo.insert_row(
            {
                "shipment_no": "PAID-KEEP-001",
                "customer": "客户A",
                "payment_status": "PAID",
                "created_time": now,
                "updated_time": now,
            }
        )

        dps_row = {
            **SAMPLE_DELIVERED,
            "odd": "PAID-KEEP-001",
            "clientUserNickName": "DPS客户",
            "clientVerifyStatus": 0,
        }
        stats = _upsert_dps_rows(repo, [dps_row])
        self.assertEqual(stats["unchanged"], 1)

        saved = repo.get_by_shipment_no("PAID-KEEP-001")
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved["paymentStatus"], "PAID")
        self.assertEqual(saved["customer"], "客户A")
        db.conn.close()
        tmp.cleanup()

    def test_sync_upgrades_unpaid_to_paid_when_dps_paid(self) -> None:
        from youzi_v2.services.shipment_dps_sync import _upsert_dps_rows

        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        repo = ShipmentsRepository(db)
        now = "2026-07-11 12:00:00"
        repo.insert_row(
            {
                "shipment_no": "UNPAID-UPGRADE-001",
                "customer": "客户B",
                "payment_status": "UNPAID",
                "created_time": now,
                "updated_time": now,
            }
        )

        dps_row = {
            **SAMPLE_DELIVERED,
            "odd": "UNPAID-UPGRADE-001",
            "clientVerifyStatus": 1,
        }
        stats = _upsert_dps_rows(repo, [dps_row])
        self.assertEqual(stats["failed"], 0)

        saved = repo.get_by_shipment_no("UNPAID-UPGRADE-001")
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved["paymentStatus"], "PAID")
        db.conn.close()
        tmp.cleanup()

    def test_sync_keeps_unpaid_when_dps_unpaid(self) -> None:
        from youzi_v2.services.shipment_dps_sync import _upsert_dps_rows

        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "t.db")
        repo = ShipmentsRepository(db)
        now = "2026-07-11 12:00:00"
        repo.insert_row(
            {
                "shipment_no": "UNPAID-KEEP-001",
                "customer": "客户B",
                "payment_status": "UNPAID",
                "created_time": now,
                "updated_time": now,
            }
        )

        dps_row = {
            **SAMPLE_DELIVERED,
            "odd": "UNPAID-KEEP-001",
            "clientVerifyStatus": 0,
        }
        stats = _upsert_dps_rows(repo, [dps_row])
        self.assertEqual(stats["failed"], 0)

        saved = repo.get_by_shipment_no("UNPAID-KEEP-001")
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved["paymentStatus"], "UNPAID")
        db.conn.close()
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
