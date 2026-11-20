"""订单流转只保存专用授权，复用当前手动刷新的快照逻辑。"""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from .services import order_flow_sync as flow
from .services.daily_sync import save_authorization


class OrderFlowAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'config.json'
        self.path.write_text(json.dumps({'dps_authorization':'Bearer EXAMPLE-SHIPMENT',
            'dps_ddlz_authorization':'Bearer EXAMPLE-OLD-FLOW','other':True}),encoding='utf-8')
        self.db=Mock()
        self.patches=[patch.object(flow,'get_order_flow_poll_settings',return_value=SimpleNamespace(enabled=True,last_finished=None)),
                      patch.object(flow,'record_order_flow_poll_finished'),patch.object(flow,'OrderFlowRepository'),
                      patch.object(flow,'fetch_order_flow_rows',return_value=[{'waybillNo':'EXAMPLE-ORDER'}])]
        self.mocks=[p.start() for p in self.patches]
        self.mocks[2].return_value.apply_snapshot.return_value={'remote':1,'created':1,'changed':0,'ended':0}
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def test_saves_only_flow_auth_and_uses_one_fetch_then_same_snapshot(self):
        result=flow.run_order_flow_sync(self.db,self.path,force=True,authorization='EXAMPLE-NEW-FLOW')
        config=json.loads(self.path.read_text())
        self.assertEqual(config['dps_authorization'],'Bearer EXAMPLE-SHIPMENT')
        self.assertEqual(config['dps_ddlz_authorization'],'Bearer EXAMPLE-NEW-FLOW')
        self.assertTrue(config['other'])
        self.mocks[3].assert_called_once_with(self.path,authorization='Bearer EXAMPLE-NEW-FLOW')
        self.mocks[2].return_value.apply_snapshot.assert_called_once_with([{'waybillNo':'EXAMPLE-ORDER'}])
        self.assertTrue(result['authorizationSaved'])
        self.assertNotIn('EXAMPLE-NEW-FLOW',str(result))

    def test_fetch_failure_keeps_old_auth_and_snapshot(self):
        self.mocks[3].side_effect=ValueError('echo EXAMPLE-NEW-FLOW')
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'未保存新授权'):
            flow.run_order_flow_sync(self.db,self.path,force=True,authorization='EXAMPLE-NEW-FLOW')
        self.assertEqual(self.path.read_bytes(),before)
        self.mocks[2].assert_not_called()

    def test_skip_while_running_does_not_save(self):
        before=self.path.read_bytes()
        flow._lock.acquire()
        try:
            result=flow.run_order_flow_sync(self.db,self.path,force=True,authorization='EXAMPLE-NEW-FLOW')
        finally: flow._lock.release()
        self.assertTrue(result['skipped'])
        self.assertEqual(self.path.read_bytes(),before)
        self.mocks[3].assert_not_called()

    def test_empty_reuses_current_and_does_not_save(self):
        before=self.path.read_bytes()
        result=flow.run_order_flow_sync(self.db,self.path,force=True,authorization='')
        self.assertFalse(result['authorizationSaved'])
        self.assertEqual(self.path.read_bytes(),before)
        self.mocks[3].assert_called_once_with(self.path,authorization='Bearer EXAMPLE-OLD-FLOW')

    def test_existing_manual_refresh_unchanged(self):
        flow.run_order_flow_sync(self.db,self.path,force=True)
        self.mocks[3].assert_called_once_with(self.path)

    def test_save_failure_does_not_apply_snapshot(self):
        with patch.object(flow,'save_authorization',side_effect=OSError('example')):
            with self.assertRaisesRegex(ValueError,'保存失败'):
                flow.run_order_flow_sync(self.db,self.path,force=True,authorization='EXAMPLE-NEW-FLOW')
        self.mocks[2].assert_not_called()

    def test_snapshot_failure_reports_auth_saved_separately(self):
        self.mocks[2].return_value.apply_snapshot.side_effect=ValueError('example')
        with self.assertRaisesRegex(ValueError,'授权已保存'):
            flow.run_order_flow_sync(self.db,self.path,force=True,authorization='EXAMPLE-NEW-FLOW')
        self.assertEqual(json.loads(self.path.read_text())['dps_ddlz_authorization'],'Bearer EXAMPLE-NEW-FLOW')
