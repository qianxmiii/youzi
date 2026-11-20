import json
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from youzi_v2.services.shipment_dps_route_status_sync import pick_latest_milestone_from_nodes
from youzi_v2.services.shipment_route_add import add_routes, route_options, route_presets, save_route_presets


class Clock(datetime):
    @classmethod
    def now(cls):
        return cls(2026, 11, 20, 10, 20, 30)


class RouteAddTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('CREATE TABLE shipment_route_status_codes(code TEXT, name_zh TEXT, dps_status TEXT, sort_order INT, is_active INT)')
        self.conn.executemany('INSERT INTO shipment_route_status_codes VALUES(?,?,?,?,?)', [
            ('INFO', '信息传递', '100', 0, 0),
            ('SIGNED', '签收', '601', 1, 1),
            ('CUSTOM', '自定义', '777', 2, 1),
            ('OFF', '停用', '999', 3, 0),
        ])
        self.repo = Mock()
        self.repo._database.conn = self.conn
        self.repo._database.lock = threading.RLock()
        self.repo.get_by_id.side_effect = lambda key: dict(id=key, shipmentNo='SYNTHETIC-' + key, waybillId='WB-' + key)
        self.config = {'dps_updateRoute': {'url': 'https://example.invalid/routes', 'method': 'POST'}, 'dps_authorization': 'SYNTHETIC'}

    def run_add(self, ids=('A',), **kwargs):
        with patch('youzi_v2.services.shipment_route_add.load_config_json', return_value=self.config), patch('youzi_v2.services.shipment_route_add.datetime', Clock):
            return add_routes(self.repo, Path('unused'), list(ids), kwargs.get('node_time'),
                              kwargs.get('estimated_delivery_date'), kwargs.get('node_desc', 'Synthetic node'), kwargs.get('status', '601'))

    def test_preset_save_preserves_config_and_rejects_invalid_changes(self):
        active = {'label': '签收', 'status': '601', 'text': 'Delivered'}
        inactive = {'label': '旧节点', 'status': '999', 'text': 'Inactive node'}
        self.config['dps_updateRoute']['presets'] = [inactive]
        statuses = route_options(self.repo)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text(json.dumps(self.config), encoding='utf-8')
            self.assertEqual(save_route_presets(path, statuses, [active, inactive]), [active, inactive])
            self.assertEqual(route_presets(path), [active, inactive])
            saved = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(saved['dps_authorization'], self.config['dps_authorization'])
            self.assertEqual(saved['dps_updateRoute']['url'], self.config['dps_updateRoute']['url'])
            with self.assertRaises(ValueError):
                save_route_presets(path, statuses, [active, active])
            with self.assertRaises(ValueError):
                save_route_presets(path, statuses, [{**inactive, 'text': 'Changed'}])
            self.assertEqual(route_presets(path), [active, inactive])
            save_route_presets(path, statuses, [])
            self.assertEqual(route_presets(path), [])

    def test_payload_defaults_and_explicit_dates(self):
        response = Mock(status_code=200)
        response.json.return_value = {'code': 200}
        with patch('youzi_v2.services.shipment_route_add.requests.request', return_value=response) as request:
            result = self.run_add(ids=('A', 'A'))
            self.assertEqual(result['succeeded'], 1)
            request.assert_called_once()
            body = request.call_args.kwargs['json']
            self.assertEqual(set(body), {'commerceWaybillId', 'nodeTime', 'estimatedDeliveryDate', 'nodeDesc', 'status'})
            self.assertEqual(body['nodeTime'], '2026-11-20 10:20:30')
            self.assertEqual(body['estimatedDeliveryDate'], '2026-12-05 10:20:30')
            self.assertEqual(body['status'], '601')
            self.run_add(node_time='2026-11-01 08:30:00', estimated_delivery_date='2026-12-10 09:30:00', status='777')
            self.assertEqual(request.call_args.kwargs['json']['nodeTime'], '2026-11-01 08:30:00')

    def test_preflight_rejects_invalid_data_before_any_write(self):
        with patch('youzi_v2.services.shipment_route_add.requests.request') as request:
            for values in [{'status': '999'}, {'node_time': 'not a date'}, {'node_desc': '   '}, {'ids': ()}]:
                with self.assertRaises(ValueError):
                    self.run_add(**values)
            self.repo.get_by_id.side_effect = lambda key: dict(id=key, shipmentNo=key, waybillId='DUPLICATE')
            with self.assertRaises(ValueError):
                self.run_add(ids=('A', 'B'))
            request.assert_not_called()
        self.assertEqual([option['value'] for option in route_options(self.repo)], ['601', '777', '100'])

    def test_information_can_be_saved_and_submitted_without_becoming_latest_milestone(self):
        preset = {'label': '信息通知', 'status': '100', 'text': 'Update provided'}
        with patch('youzi_v2.services.shipment_route_add.update_logistics_config') as update:
            update.side_effect = lambda _path, apply: apply(self.config)
            save_route_presets(Path('unused'), route_options(self.repo), [preset])
        self.assertEqual(self.config['dps_updateRoute']['presets'], [preset])

        response = Mock(status_code=200)
        response.json.return_value = {'code': 200}
        with patch('youzi_v2.services.shipment_route_add.requests.request', return_value=response) as request:
            result = self.run_add(status='100', node_desc=preset['text'])
            self.assertEqual(result['succeeded'], 1)
            self.assertEqual(request.call_args.kwargs['json']['status'], '100')

        milestone = {'status': '306', 'nodeTime': '2026-11-20 10:00:00'}
        information = {'status': '100', 'nodeTime': '2026-11-20 11:00:00'}
        self.assertEqual(pick_latest_milestone_from_nodes([information, milestone]), ('ARRIVED_POD', milestone))

    def test_unresolved_appointment_date_cannot_be_sent(self):
        with patch('youzi_v2.services.shipment_route_add.requests.request') as request:
            for placeholder, field in (
                ('{预计交仓日期}', '预计交仓日期'),
                ('N/N', '预计交仓日期'),
                ('{完成派送日期}', '完成派送日期'),
            ):
                with self.subTest(placeholder=placeholder), self.assertRaisesRegex(ValueError, f'{field}尚未填写'):
                    self.run_add(node_desc=f'Expected to be delivered ({placeholder})')
            request.assert_not_called()

    def test_warehouse_placeholder_is_resolved_per_shipment(self):
        self.repo.get_by_id.side_effect = lambda key: dict(
            id=key, shipmentNo=key, waybillId=f'WB-{key}', addressCode={'A': ' TEST1 ', 'B': 'TEST2'}.get(key),
        )
        response = Mock(status_code=200)
        response.json.return_value = {'code': 200}
        description = 'Delivered to {派送仓库} on 10/21 local time.（{派送仓库}当地时间10/21-已完成派送）'
        with patch('youzi_v2.services.shipment_route_add.requests.request', return_value=response) as request:
            with self.assertRaisesRegex(ValueError, '缺少派送仓库'):
                self.run_add(ids=('A', 'C'), node_desc=description)
            request.assert_not_called()
            result = self.run_add(ids=('A', 'B'), node_desc=description)
            self.assertEqual(result['succeeded'], 2)
            self.assertEqual(
                {call.kwargs['json']['commerceWaybillId']: call.kwargs['json']['nodeDesc'] for call in request.call_args_list},
                {
                    'WB-A': 'Delivered to TEST1 on 10/21 local time.（TEST1当地时间10/21-已完成派送）',
                    'WB-B': 'Delivered to TEST2 on 10/21 local time.（TEST2当地时间10/21-已完成派送）',
                },
            )

    def test_batch_partial_results_and_timeout_are_not_retried(self):
        def send(method, url, **kwargs):
            wb = kwargs['json']['commerceWaybillId']
            if wb == 'WB-C':
                raise requests.Timeout()
            response = Mock(status_code=200)
            response.json.return_value = {'code': 200 if wb == 'WB-A' else 500}
            return response
        with patch('youzi_v2.services.shipment_route_add.requests.request', side_effect=send) as request:
            result = self.run_add(ids=('A', 'B', 'C'))
            self.assertEqual([r['status'] for r in result['items']], ['success', 'failed', 'unknown'])
            self.assertEqual((result['succeeded'], result['failed'], result['unknown']), (1, 1, 1))
            self.assertEqual(request.call_count, 3)


if __name__ == '__main__':
    unittest.main()
