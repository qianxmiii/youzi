import threading
import unittest
from unittest.mock import Mock, patch

from youzi_v2.db.shipment_sla_alerts_repository import ShipmentSlaAlertsRepository


def alert(key, delta, status='open', risk='severe_overdue', kind='DELIVERY_TIME'):
    return dict(id=key, shipmentNo=key, daysUntilDue=delta,
                overdueDays=max(0, -(delta or 0)), status=status, riskLevel=risk,
                alertType=kind, alertTypes=[kind], dueDate='2026-01-01')


class TransportAttentionSortTests(unittest.TestCase):
    def query(self, rows, **params):
        database = Mock()
        database.lock = threading.RLock()
        database.conn.execute.return_value.fetchall.return_value = rows
        repo = ShipmentSlaAlertsRepository(database)
        with patch.object(repo, '_load_channel_rules_grouped', return_value={}), patch(
            'youzi_v2.db.shipment_sla_alerts_repository._alert_to_api', side_effect=lambda row, **_: row
        ):
            return repo.list_alerts(**params)

    def test_global_order_precedes_pagination_and_followup_status(self):
        rows = [alert('short', -2), alert('long', -20, status='acknowledged'),
                alert('middle', -8), alert('last', -1)]
        first = self.query(rows, limit=2)
        second = self.query(rows, limit=2, offset=2)
        self.assertEqual([r['id'] for r in first['items']], ['long', 'middle'])
        self.assertEqual([r['id'] for r in second['items']], ['short', 'last'])
        self.assertEqual(first['total'], 4)

    def test_observation_and_missing_dates_use_displayed_signed_days(self):
        rows = [alert('far', 7, risk='warning_soon'), alert('missing', None, risk='warning_soon'),
                alert('near', 1, risk='warning_soon'), alert('today', 0, risk='warning_soon')]
        result = self.query(rows, risk_level='warning_soon')
        self.assertEqual([r['id'] for r in result['items']], ['today', 'near', 'far', 'missing'])

    def test_history_is_sorted_and_same_shipment_is_still_merged_in_todo(self):
        short = alert('same-short', -3)
        long = alert('same-long', -12, kind='WAREHOUSE_NO_DEPARTURE')
        short['shipmentNo'] = long['shipmentNo'] = 'same'
        result = self.query([short, alert('other', -6), long])
        self.assertEqual(result['total'], 2)
        self.assertEqual([r['shipmentNo'] for r in result['items']], ['same', 'other'])
        self.assertEqual(len(result['items'][0]['relatedAlertIds']), 2)
        history = self.query([alert('short', -2), alert('long', -9, status='resolved')], scope='all')
        self.assertEqual([r['id'] for r in history['items']], ['long', 'short'])


if __name__ == '__main__':
    unittest.main()
