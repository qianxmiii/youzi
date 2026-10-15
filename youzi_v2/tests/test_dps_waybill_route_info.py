"""DPS 明细状态轨迹查询（URL 仅来自 config，测试用占位地址）。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from youzi_v2.db.connection import Database
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.services.dps_waybill_route_info import (
    build_waybill_route_info_url,
    load_waybill_route_info_config,
    require_waybill_route_info_config,
)
from youzi_v2.services.shipment_dps_route_status_sync import (
    extract_route_milestone_times,
    pick_latest_milestone_from_nodes,
    sync_route_status_by_waybill_ids,
)

_FAKE_ROUTE_URL = "https://example.test/dps/route-status"


class DpsWaybillRouteInfoConfigTest(unittest.TestCase):
    def test_requires_url_in_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "shipment_queryByOrder": {
                            "url": "https://example.test/order",
                            "Authorization": "Bearer tok",
                        }
                    }
                ),
                encoding="utf-8",
            )
            cfg = load_waybill_route_info_config(path)
            self.assertEqual(cfg["url"], "")
            with self.assertRaises(ValueError):
                require_waybill_route_info_config(path)

    def test_load_url_and_auth_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "dps_route_status_query": {"url": _FAKE_ROUTE_URL},
                        "shipment_queryByOrder": {
                            "url": "https://example.test/order",
                            "Authorization": "Bearer tok",
                        },
                    }
                ),
                encoding="utf-8",
            )
            cfg = load_waybill_route_info_config(path)
            self.assertEqual(cfg["url"], _FAKE_ROUTE_URL)
            self.assertEqual(cfg["authorization"], "Bearer tok")

    def test_build_url_appends_waybill_id(self) -> None:
        url = build_waybill_route_info_url(_FAKE_ROUTE_URL, "2096160449776230401")
        self.assertTrue(url.startswith(_FAKE_ROUTE_URL))
        self.assertIn("commerceWaybillId=2096160449776230401", url)


class PickMilestoneTest(unittest.TestCase):
    def test_skips_info_and_picks_latest_milestone(self) -> None:
        nodes = [
            {"nodeTime": "2026-10-06 10:15:00", "status": "601"},
            {"nodeTime": "2026-10-05 20:55:40", "status": "510"},
            {"nodeTime": "2026-09-28 17:46:34", "status": "100"},
        ]
        code, node = pick_latest_milestone_from_nodes(nodes)
        self.assertEqual(code, "TRACK_SIGNED")
        self.assertEqual(node.get("status"), "601")

    def test_only_info_returns_none_code(self) -> None:
        code, node = pick_latest_milestone_from_nodes(
            [{"nodeTime": "2026-01-01 00:00:00", "status": "100"}]
        )
        self.assertIsNone(code)
        self.assertIsNotNone(node)


class SyncRouteStatusByWaybillTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        self.repo = ShipmentsRepository(self.db)
        self.cfg = Path(self.tmp.name) / "config.json"
        self.cfg.write_text(
            json.dumps(
                {
                    "dps_route_status_query": {"url": _FAKE_ROUTE_URL},
                    "shipment_queryByOrder": {
                        "url": "https://example.test/order",
                        "Authorization": "Bearer tok",
                    },
                }
            ),
            encoding="utf-8",
        )
        self.repo.upsert_by_shipment_no(
            {
                "shipment_no": "DPSECO260915022",
                "status_code": "IN_TRANSIT",
                "waybill_id": "2096160449776230401",
                "route_status": "WAREHOUSE_IN",
            }
        )

    def tearDown(self) -> None:
        self.db.conn.close()
        self.tmp.cleanup()

    def test_extract_route_milestone_times_earliest(self) -> None:
        times = extract_route_milestone_times(
            [
                {"status": "202", "nodeTime": "2026-09-01 08:00:00"},
                {"status": "306", "nodeTime": "2026-09-20 12:00:00"},
                {"status": "502", "nodeTime": "2026-09-25 09:00:00"},
                {"status": "202", "nodeTime": "2026-09-02 08:00:00"},
            ]
        )
        self.assertEqual(times["route_warehouse_in_time"], "2026-09-01 08:00:00")
        self.assertEqual(times["route_arrived_pod_time"], "2026-09-20 12:00:00")
        self.assertEqual(
            times["route_dest_transit_warehouse_time"], "2026-09-25 09:00:00"
        )

    def test_sync_updates_route_status(self) -> None:
        nodes = [
            {
                "nodeTime": "2026-10-06 10:15:00",
                "nodeDesc": "signed",
                "status": "601",
                "estimatedDeliveryDate": "2026-10-08 10:55:44",
            },
            {
                "nodeTime": "2026-10-05 20:55:40",
                "nodeDesc": "handover",
                "status": "510",
            },
            {
                "nodeTime": "2026-09-01 08:00:00",
                "nodeDesc": "warehouse in",
                "status": "202",
            },
            {
                "nodeTime": "2026-09-20 12:00:00",
                "nodeDesc": "arrived pod",
                "status": "306",
            },
            {
                "nodeTime": "2026-09-25 09:00:00",
                "nodeDesc": "dest transit",
                "status": "502",
            },
        ]
        with patch(
            "youzi_v2.services.shipment_dps_route_status_sync.query_waybill_route_info",
            return_value=nodes,
        ):
            result = sync_route_status_by_waybill_ids(
                self.repo,
                self.cfg,
                ["DPSECO260915022"],
            )
        self.assertEqual(result["updated"], 1)
        ship = self.repo.get_by_shipment_no("DPSECO260915022")
        assert ship is not None
        self.assertEqual(ship["routeStatus"], "TRACK_SIGNED")
        self.assertEqual(ship["expectedDeliveryTime"], "2026-10-08 10:55:44")
        self.assertEqual(ship["routeWarehouseInTime"], "2026-09-01 08:00:00")
        self.assertEqual(ship["routeArrivedPodTime"], "2026-09-20 12:00:00")
        self.assertEqual(
            ship["routeDestTransitWarehouseTime"], "2026-09-25 09:00:00"
        )

    def test_skip_without_waybill_id(self) -> None:
        self.repo.upsert_by_shipment_no(
            {
                "shipment_no": "NO-WID",
                "status_code": "IN_TRANSIT",
            }
        )
        result = sync_route_status_by_waybill_ids(
            self.repo,
            self.cfg,
            ["NO-WID"],
        )
        self.assertEqual(result["missingWaybillId"], 1)
        self.assertEqual(result["updated"], 0)


if __name__ == "__main__":
    unittest.main()
