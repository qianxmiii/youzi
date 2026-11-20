"""每日同步测试：临时配置、内存数据库、模拟远端，不访问真实授权/运单。"""
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from .db.task_history import ensure_schema, list_tasks
from .services.daily_sync import DailySyncManager, STEPS, validate_authorization, save_authorization
from .services import sync_coordination as gate


class DailySyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'config.json'
        self.path.write_text(json.dumps({'dps_authorization':'Bearer EXAMPLE-OLD',
            'shipment_queryByPerson':{'url':'https://example.invalid/query?pageSize=50'},
            'untouched':{'example':True}}), encoding='utf-8')
        self.db = SimpleNamespace(conn=sqlite3.connect(':memory:', check_same_thread=False), lock=threading.RLock())
        ensure_schema(self.db.conn)
        self.queue = []
        self.order = []
        self.runners = {key: self.runner(key) for key, _ in STEPS}
        self.manager = DailySyncManager(self.db, self.path, self.runners,
            validator=lambda *_: None, launch=self.queue.append)

    def tearDown(self):
        # 每条测试在异常前后均释放租约，防止并发用例污染其他测试。
        while self.queue:
            self.queue.pop(0)()
        self.db.conn.close()
        self.temp.cleanup()

    def runner(self, key):
        def run(start, end, log):
            self.order.append(key)
            return {'total':2, 'updated':1, 'unchanged':1}
        return run

    def start(self, **kwargs):
        return self.manager.start('EXAMPLE-NEW', start='2026-11-01', end='2026-11-30', **kwargs)

    def finish(self):
        self.queue.pop(0)()
        return self.manager.latest()

    def test_six_steps_order_and_no_secret_in_api_or_history(self):
        first = self.start()
        self.assertEqual(first['status'], 'queued')
        self.assertEqual(self.order, [])
        result = self.finish()
        self.assertEqual(self.order, [k for k, _ in STEPS])
        self.assertEqual(result['status'], 'done')
        self.assertNotIn('EXAMPLE-NEW', json.dumps(result))
        self.assertNotIn('EXAMPLE-NEW', json.dumps(list_tasks(self.db)))
        cfg = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertTrue(cfg['untouched']['example'])
        self.assertEqual(cfg['dps_authorization'], 'Bearer EXAMPLE-NEW')
        self.assertEqual(list_tasks(self.db)[0]['managedBy'], 'server')

    def test_invalid_authorization_does_not_save_or_create_job(self):
        self.manager.validator = Mock(side_effect=ValueError('验证失败'))
        before = self.path.read_bytes()
        with self.assertRaises(ValueError): self.start()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertIsNone(self.manager.latest())
        self.assertFalse(self.queue)

    def test_invalid_date_does_not_save_authorization(self):
        before = self.path.read_bytes()
        with self.assertRaises(ValueError): self.manager.start('EXAMPLE-NEW', start='invalid', end='invalid')
        self.assertEqual(self.path.read_bytes(), before)

    def test_existing_auth_can_be_used_without_clearing(self):
        self.manager.start('', start='2026-11-01', end='2026-11-30')
        self.finish()
        self.assertEqual(json.loads(self.path.read_text())['dps_authorization'], 'Bearer EXAMPLE-OLD')

    def test_duplicate_start_and_manual_sync_blocked_including_during_validation(self):
        @gate.serialized_sync
        def manual(): return True
        def validate(*_):
            with self.assertRaises(gate.SyncBusy): manual()
        self.manager.validator = validate
        self.start()
        with self.assertRaises(gate.SyncBusy): self.start()
        with self.assertRaises(gate.SyncBusy): manual()
        self.finish()
        self.assertTrue(manual())

    def test_scheduled_conflict_is_explicit_skip_not_success_or_exception(self):
        @gate.serialized_sync
        def scheduled(*, trigger): return {'updated':1}
        self.start()
        skipped = scheduled(trigger='scheduled')
        self.assertTrue(skipped['skipped'])
        self.assertTrue(skipped['intervalSkipped'])
        self.finish()

    def test_running_and_resumable_history_cannot_be_deleted(self):
        from .db.task_history import delete_task
        self.runners['route'] = lambda *_: {'failed':1}
        first=self.start()
        with self.assertRaises(ValueError): delete_task(self.db, first['id'])
        self.finish()
        with self.assertRaises(ValueError): delete_task(self.db, first['id'])

    def test_close_retains_failed_history_and_allows_new_round(self):
        self.runners['route'] = lambda *_: {'failed':1}
        first=self.start(); self.finish()
        closed=self.manager.close(first['id'])
        self.assertEqual(closed['status'],'closed')
        self.assertEqual(list_tasks(self.db)[0]['state'],'failed')
        self.assertFalse(list_tasks(self.db)[0]['resumable'])
        self.assertEqual(closed['steps'][-1]['stats']['failed'],1)
        next_run=self.start()
        self.assertNotEqual(next_run['id'],first['id'])
        self.finish()

    def test_real_background_thread_finishes_without_request_waiting(self):
        entered, finish = threading.Event(), threading.Event()
        original = self.runners['pickup']
        def slow(*args):
            entered.set()
            finish.wait(3)
            return original(*args)
        self.runners['pickup'] = slow
        thread = []
        def launch(fn):
            worker=threading.Thread(target=fn);thread.append(worker);worker.start()
        self.manager.launch = launch
        try:
            first=self.start()
            self.assertEqual(first['status'],'queued')
            self.assertTrue(entered.wait(3))
            self.assertEqual(self.manager.latest()['status'],'running')
        finally:
            finish.set()
            for worker in thread: worker.join(5)
        self.assertEqual(self.manager.latest()['status'],'done')

    def test_waits_for_auth_and_resume_skips_successful_steps(self):
        def expire(*_): raise gate.DpsAuthorizationExpired()
        self.runners['transit'] = expire
        self.start()
        paused = self.finish()
        self.assertEqual(paused['status'], 'waiting_authorization')
        self.assertEqual(self.order, ['pickup','warehoused'])
        self.runners['transit'] = self.runner('transit')
        self.manager.start('EXAMPLE-REPLACED', resume_id=paused['id'], start='2099-01-01', end='2099-02-01')
        result = self.finish()
        self.assertEqual(result['status'], 'done')
        self.assertEqual(result['start'], paused['start'])
        self.assertEqual(self.order, [k for k, _ in STEPS])

    def test_partial_continues_other_steps_and_resume_only_pending_rows(self):
        attempts = []
        attempt = [0]
        def rows_runner(*_):
            attempt[0] += 1
            rows = gate.pending_rows(lambda ids: [{'id':x} for x in (ids if ids is not None else ['EXAMPLE-A','EXAMPLE-B'])], lambda r:r['id'])
            for row in gate.checkpointed_rows(rows, lambda r:r['id']):
                attempts.append(row['id'])
                if row['id'] == 'EXAMPLE-B' and attempt[0] == 1: gate.retry_item()
            return {'total':len(rows), 'errors':['example error'] if attempt[0] == 1 else []}
        self.runners['internal'] = rows_runner
        self.start(); first = self.finish()
        self.assertEqual(first['status'],'partial')
        self.assertEqual(first['steps'][3]['pendingCount'],1)
        self.assertEqual(self.order, ['pickup','warehoused','transit','carrier','route'])
        self.manager.start('', resume_id=first['id'])
        second = self.finish()
        self.assertEqual(second['status'],'done')
        self.assertEqual(attempts,['EXAMPLE-A','EXAMPLE-B','EXAMPLE-B'])
        self.assertNotIn('candidates', json.dumps(second))

    def test_error_text_is_redacted(self):
        def fail(start,end,log):
            log('Bearer EXAMPLE-NEW')
            return {'errors':['echo Bearer EXAMPLE-NEW']}
        self.runners['route'] = fail
        self.start(); self.finish()
        self.assertNotIn('EXAMPLE-NEW',json.dumps(self.manager.latest()))
        self.assertNotIn('EXAMPLE-NEW',json.dumps(list_tasks(self.db)))

    def test_process_restart_marks_incomplete_job_interrupted(self):
        self.start()
        # 模拟旧进程消失：不执行其线程，仅释放进程本地租约。
        self.queue.clear()
        gate.release(gate._owner)
        recovered = DailySyncManager(self.db, self.path, self.runners, validator=lambda *_:None, launch=self.queue.append)
        self.assertEqual(recovered.latest()['status'], 'interrupted')
        recovered.start('', resume_id=recovered.latest()['id'])
        self.finish()

    def test_thread_launch_failure_separately_reports_saved_authorization(self):
        self.manager.launch = Mock(side_effect=RuntimeError('thread unavailable'))
        with self.assertRaisesRegex(ValueError, '授权已保存'):
            self.start()
        self.assertEqual(self.manager.latest()['status'],'interrupted')
        self.assertEqual(json.loads(self.path.read_text())['dps_authorization'],'Bearer EXAMPLE-NEW')

    def test_atomic_save_failure_leaves_original_intact(self):
        before=self.path.read_bytes()
        with patch('youzi_v2.services.shipment_query_config.os.replace',side_effect=OSError('example')):
            with self.assertRaises(OSError): save_authorization(self.path,'Bearer EXAMPLE-OTHER')
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(list(self.path.parent.glob('.logistics-config-*')),[])

    @patch('youzi_v2.services.daily_sync.requests.get')
    def test_validation_requires_valid_body_and_does_not_treat_403_as_expired(self, get):
        config=json.loads(self.path.read_text())
        response=get.return_value
        response.status_code=200; response.json.return_value={'code':200,'rows':[]}
        validate_authorization(config,'Bearer EXAMPLE')
        self.assertFalse(get.call_args.kwargs['allow_redirects'])
        self.assertIn('pageSize=1',get.call_args.args[0])
        response.status_code=401
        with self.assertRaisesRegex(ValueError,'授权无效'): validate_authorization(config,'Bearer EXAMPLE')
        response.status_code=403
        with self.assertRaisesRegex(ValueError,'HTTP'): validate_authorization(config,'Bearer EXAMPLE')
        response.status_code=200; response.json.return_value={'code':401,'msg':'EXAMPLE'}
        with self.assertRaisesRegex(ValueError,'授权无效'): validate_authorization(config,'Bearer EXAMPLE')
        response.json.return_value={'code':200,'rows':'wrong'}
        with self.assertRaisesRegex(ValueError,'有效运单列表'): validate_authorization(config,'Bearer EXAMPLE')


class TrackingResumeTests(unittest.TestCase):
    def test_internal_resume_preserves_incremental_merge_and_skips_completed(self):
        from .services import tracking_sync as tracking
        from .services.daily_sync import _Runtime
        step = {'candidates':['EXAMPLE-A','EXAMPLE-B'], 'completed':['EXAMPLE-A']}
        ctx = _Runtime(step, lambda:None, str)
        token=gate.runtime.set(ctx)
        repo=Mock()
        repo.list_for_tracking_sync.return_value=[{'tracking_number':sn,'status_code':'IN_TRANSIT'} for sn in step['candidates']]
        logs=Mock();logs.merge_logs_for_shipment.return_value=1;logs.count_by_shipment_no.return_value=1
        try:
            with patch.object(tracking,'load_logistics_config',return_value={'base_url':'https://example.invalid/track'}), \
                 patch.object(tracking,'query_logistics_api',return_value=([{'odd':'EXAMPLE-B'}],[])), \
                 patch.object(tracking,'logs_from_api_item',return_value=[('2026-11-01 00:00:00','example')]), \
                 patch.object(tracking,'evaluate_groups_after_tracking_sync',return_value={}), \
                 patch.object(tracking,'evaluate_sla_after_tracking_sync',return_value={}), \
                 patch.object(tracking,'recalculate_for_shipment_nos',return_value={}):
                result=tracking.sync_all_tracking(repo,logs,Path('example.json'))
            self.assertEqual(result['total'],1)
            self.assertEqual(repo.list_for_tracking_sync.call_args.args[0],['EXAMPLE-A','EXAMPLE-B'])
            self.assertTrue(repo.list_for_tracking_sync.call_args.kwargs['include_delivered'])
            logs.merge_logs_for_shipment.assert_called_once()
            logs.replace_for_shipment.assert_not_called()
            self.assertEqual(set(step['completed']),{'EXAMPLE-A','EXAMPLE-B'})
        finally:
            gate.runtime.reset(token)


if __name__ == '__main__': unittest.main()
