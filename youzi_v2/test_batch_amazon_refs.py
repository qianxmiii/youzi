import unittest
from unittest.mock import Mock, patch
from .services.batch_amazon_refs import parse_lines, process_row

class BatchAmazonRefsTests(unittest.TestCase):
    def test_formats_and_duplicates(self):
        rows = parse_lines("EXAMPLE-A = FBA-A REF-A\\\nEXAMPLE-B FBA-B REF-B")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["referenceId"], "REF-A")
        self.assertFalse(rows[1]["error"])
        self.assertTrue(all(x["error"] for x in parse_lines("A F R\nA F2 R2")))

    def test_conflict_never_saves_or_pushes(self):
        repo = Mock()
        repo.get_by_shipment_no.return_value = {"customerShipmentId": "EXISTING"}
        result = process_row(repo, None, parse_lines("A F R")[0])
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["existingShipmentId"], "EXISTING")
        repo.update_row.assert_not_called()

    @patch("youzi_v2.services.batch_amazon_refs.record_amz_push_result")
    @patch("youzi_v2.services.batch_amazon_refs.push_amz_update", return_value={"ok":False,"message":"failed"})
    @patch("youzi_v2.services.batch_amazon_refs.preview_amz_push", return_value={"originPort":"AAA","destinationPort":"BBB"})
    def test_push_failure_keeps_saved_result(self, preview, push, record):
        repo = Mock()
        repo.get_by_shipment_no.return_value = {"id":"example","customerShipmentId":"1"}
        result = process_row(repo, None, parse_lines("A F R")[0])
        self.assertEqual(result["status"], "saved")
        repo.update_row.assert_called_once()
        push.assert_called_once()
        record.assert_called_once()
