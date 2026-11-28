import unittest
from pathlib import Path

from youzi_v2.db.connection import Database
from youzi_v2.services.bills_of_lading import get_bill, list_bills, record_customs_nodes, save_binding


class BillOfLadingTest(unittest.TestCase):
    def setUp(self):
        self.database = Database(Path(":memory:"))
        self.conn = self.database.conn
        self.addCleanup(self.conn.close)
        self.conn.executemany("""
            INSERT INTO shipments
                (id, shipment_no, bill_of_lading_no, container_no, country_code, vessel_voyage, created_time, updated_time)
            VALUES (?, ?, ?, ?, ?, ?, '', '')
        """, [
            ("1", "TEST-1", " bill-a ", "BOX1", "US", "Old voyage"),
            ("2", "TEST-2", "BILL-A", None, "US", None),
            ("3", "TEST-3", "BILL-C", None, "CA", None),
        ])
        self.conn.execute("""
            INSERT INTO vessel_voyages (id,vessel_voyage,created_time,updated_time)
            VALUES ('voyage','Example V1','','')
        """)
        self.conn.executemany("""
            INSERT INTO voyage_port_calls
                (id,voyage_id,port_name,sequence,etd,eta,created_time,updated_time)
            VALUES (?, 'voyage', ?, ?, ?, ?, '', '')
        """, [
            ("origin", "Origin", 1, "2026-11-20", None),
            ("destination", "Destination", 2, None, "2026-12-04"),
        ])
        self.conn.commit()

    def test_membership_binding_and_live_port_dates(self):
        listed = list_bills(self.database, "US", "box1", "", 30, 0)
        self.assertEqual(listed["total"], 1)
        self.assertEqual(listed["items"][0]["shipmentCount"], 2)
        self.assertEqual(len(get_bill(self.database, "BILL-A")["containers"]), 1)
        self.assertEqual(list_bills(self.database, "", "", "", 30, 0)["total"], 2)

        with self.assertRaises(ValueError):
            save_binding(self.database, "BILL-A", "voyage", "destination", "origin")
        self.assertTrue(save_binding(self.database, "BILL-A", "voyage", "origin", "destination"))
        self.assertEqual(list_bills(self.database, "", "", "", 30, 0, voyage_id="voyage")["total"], 1)
        for port in ("origin", "destination"):
            self.assertEqual(list_bills(self.database, "", "", "", 30, 0, voyage_id="voyage", port_call_id=port)["total"], 1)
        self.assertEqual(list_bills(self.database, "", "", "", 30, 0, voyage_id="other", port_call_id="destination")["total"], 0)
        self.assertEqual(list_bills(self.database, "", "", "", 30, 0, voyage_id="voyage", port_call_id="other")["total"], 0)
        self.conn.execute("""
            INSERT INTO voyage_port_calls (id,voyage_id,port_name,sequence,created_time,updated_time)
            VALUES ('destination-return','voyage','Destination',3,'','')
        """)
        self.assertTrue(save_binding(self.database, "BILL-C", "voyage", "origin", "destination-return"))
        for port, expected in (("destination", "BILL-A"), ("destination-return", "BILL-C")):
            result = list_bills(self.database, "", "", "", 30, 0, voyage_id="voyage", port_call_id=port)
            self.assertEqual([item["billNo"] for item in result["items"]], [expected])
        self.assertEqual(list_bills(self.database, "", "", "", 30, 0, voyage_id="voyage", port_call_id="origin")["total"], 2)
        self.assertEqual(get_bill(self.database, "BILL-A")["state"], "planned")
        self.assertEqual(get_bill(self.database, "BILL-A")["binding"]["eta"], "2026-12-04")
        self.conn.execute("UPDATE voyage_port_calls SET atd='2026-11-21' WHERE id='origin'")
        self.assertEqual(get_bill(self.database, "BILL-A")["state"], "departed")
        self.assertEqual(self.conn.execute("SELECT vessel_voyage FROM shipments WHERE id='1'").fetchone()[0], "Old voyage")
        self.conn.execute("DELETE FROM voyage_port_calls WHERE id='destination'")
        self.assertEqual(get_bill(self.database, "BILL-A")["state"], "review")

    def test_latest_customs_evidence_applies_to_one_container_and_phase(self):
        record_customs_nodes(self.database, "TEST-1", [
            {"status": 402, "nodeTime": "2026-11-21 08:00:00", "nodeDesc": "Inspection"},
            {"status": 206, "nodeTime": "2026-11-20 08:00:00"},
        ])
        self.assertEqual(list_bills(self.database, "US", "", "inspection", 30, 0)["total"], 1)
        container = get_bill(self.database, "BILL-A")["containers"][0]
        self.assertEqual(container["shipmentCount"], 2)
        self.assertEqual(container["customs"]["import"]["shipmentNo"], "TEST-1")
        self.assertEqual(container["customs"]["import"]["description"], "Inspection")

        record_customs_nodes(self.database, "TEST-2", [{"status": "403", "nodeTime": "2026-11-22 08:00:00"}])
        record_customs_nodes(self.database, "TEST-2", [{"status": "402", "nodeTime": "2026-11-20 08:00:00"}])
        container = get_bill(self.database, "BILL-A")["containers"][0]
        self.assertEqual(container["customs"]["import"]["status"], "released")
        self.assertEqual(container["customs"]["export"]["status"], "inspection")

        self.conn.execute("UPDATE shipments SET container_no='BOX2' WHERE id='2'")
        containers = get_bill(self.database, "BILL-A")["containers"]
        self.assertEqual([c["customs"]["import"]["status"] for c in containers], ["inspection", "released"])

    def test_untimed_inspection_is_not_cleared_by_another_shipment(self):
        self.conn.execute("UPDATE shipments SET route_status='IMPORT_CUSTOMS_EXCEPTION' WHERE id='1'")
        record_customs_nodes(self.database, "TEST-2", [{"status": "403", "nodeTime": "2026-11-22 08:00:00"}])
        self.assertTrue(get_bill(self.database, "BILL-A")["hasInspection"])

    def test_current_inspection_is_compared_with_saved_release(self):
        record_customs_nodes(self.database, "TEST-1", [{"status": "403", "nodeTime": "2026-11-22 08:00:00"}])
        for opened_time, expected in (
            ("2026-11-21 08:00:00", "released"),
            ("2026-11-22 08:00:00", "inspection"),
            ("2026-11-23 08:00:00", "inspection"),
            (None, "inspection"),
        ):
            with self.subTest(opened_time=opened_time):
                self.conn.execute("""
                    UPDATE shipments
                    SET route_status='IMPORT_CUSTOMS_EXCEPTION',
                        exception_code='IMPORT_CUSTOMS_EXCEPTION', exception_opened_time=?
                    WHERE id='1'
                """, (opened_time,))
                bill = get_bill(self.database, "BILL-A")
                self.assertEqual(bill["containers"][0]["customs"]["import"]["status"], expected)
                self.assertEqual(bill["hasInspection"], expected == "inspection")
                self.assertEqual(list_bills(self.database, "US", "", "inspection", 30, 0)["total"], int(bill["hasInspection"]))

        self.conn.execute("UPDATE shipments SET exception_code=NULL WHERE id='1'")
        self.assertTrue(get_bill(self.database, "BILL-A")["hasInspection"])

    def test_delivery_filter_requires_every_shipment_signed(self):
        self.conn.execute("UPDATE shipments SET route_status='TRACK_SIGNED' WHERE id='1'")
        self.assertEqual(get_bill(self.database, "BILL-A")["deliveredCount"], 1)
        self.assertEqual(list_bills(self.database, "US", "", "delivered", 30, 0)["total"], 0)
        self.assertEqual(list_bills(self.database, "US", "", "", 30, 0, delivery_scope="open")["total"], 1)
        self.conn.execute("UPDATE shipments SET status_code='3' WHERE id='2'")
        result = list_bills(self.database, "US", "", "delivered", 30, 0)
        self.assertEqual([(item["billNo"], item["deliveredCount"]) for item in result["items"]], [("BILL-A", 2)])
        self.assertEqual(list_bills(self.database, "US", "", "", 30, 0, delivery_scope="open")["total"], 0)
        self.assertEqual(list_bills(self.database, "US", "", "unbound", 30, 0, delivery_scope="delivered")["total"], 1)

    def test_port_filters_use_bound_ports_and_match_unbound_shipments_as_pairs(self):
        self.conn.execute("""
            INSERT INTO port_codes (code,name_zh,name_en,created_time,updated_time)
            VALUES ('TESTOR','测试起运港','Origin','','')
        """)
        self.conn.execute("UPDATE shipments SET origin_port_code='TESTOR', destination_port_code='Other' WHERE id='1'")
        self.conn.execute("UPDATE shipments SET origin_port_code='Other', destination_port_code='Destination' WHERE id='2'")
        self.assertEqual(list_bills(self.database, "US", "", "", 30, 0, origin_port="TESTOR")["total"], 1)
        self.assertEqual(list_bills(self.database, "US", "", "", 30, 0, origin_port="TESTOR", destination_port="DESTINATION")["total"], 0)

        self.assertTrue(save_binding(self.database, "BILL-A", "voyage", "origin", "destination"))
        result = list_bills(self.database, "US", "", "", 30, 0, origin_port="TESTOR", destination_port="DESTINATION")
        self.assertEqual([item["billNo"] for item in result["items"]], ["BILL-A"])
        self.assertEqual(result["portOptions"]["origins"], [{"value": "TESTOR", "label": "测试起运港（TESTOR）"}])
        self.assertEqual(list_bills(self.database, "US", "", "", 30, 0, destination_port="OTHER")["total"], 0)


if __name__ == "__main__":
    unittest.main()
