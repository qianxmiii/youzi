import sqlite3
import threading
import unittest
from types import SimpleNamespace
from .db.task_history import ensure_schema, save_task, list_tasks, record_event, finish_event, list_events

class TaskHistoryTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.db = SimpleNamespace(conn=self.conn, lock=threading.RLock())
        ensure_schema(self.conn)
    def tearDown(self):
        self.conn.close()
    def test_upsert_and_pagination(self):
        save_task(self.db, {'id':'a','started':1,'state':'running'})
        save_task(self.db, {'id':'a','started':1,'state':'done','details':'example'})
        save_task(self.db, {'id':'b','started':2,'state':'failed'})
        self.assertEqual(len(list_tasks(self.db)),2)
        self.assertEqual(list_tasks(self.db,1)[0]['id'],'b')
        self.assertEqual(list_tasks(self.db,1,1)[0]['state'],'done')
    def test_audit_survives_absent_final_result(self):
        event = record_event(self.db,'task','EXAMPLE',{'shipmentId':'OLD'}, {'shipmentId':'NEW','force':True})
        row = list_events(self.db,'task')[0]
        self.assertEqual(row['before']['shipmentId'],'OLD')
        self.assertEqual(row['result'],{})
        finish_event(self.db,event,{'ok':False,'message':'timeout'})
        self.assertEqual(list_events(self.db,'task')[0]['result']['message'],'timeout')
        self.assertEqual(list_events(self.db,'other'),[])
