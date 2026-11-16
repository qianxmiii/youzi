import asyncio
import json
import sqlite3
import threading
import unittest
from types import SimpleNamespace
from .db.task_history import ensure_schema, save_task, list_tasks
from .services.request_task_tracking import RequestTaskTrackingMiddleware, active_ids, complete

class RequestTaskTests(unittest.TestCase):
    def test_backend_running_and_completion(self):
        conn=sqlite3.connect(':memory:')
        db=SimpleNamespace(conn=conn,lock=threading.RLock())
        ensure_schema(conn)
        save_task(db,{'id':'example-task','title':'example','started':1,'state':'running'})
        async def run():
            entered,release=asyncio.Event(),asyncio.Event()
            sent=[]
            async def app(scope,receive,send):
                entered.set()
                await release.wait()
                await send({'type':'http.response.start','status':200,'headers':[]})
                await send({'type':'http.response.body','body':json.dumps({'total':5,'updated':4,'failed':1}).encode()})
            async def send(message): sent.append(message)
            async def receive(): return {'type':'http.request','body':b''}
            wrapper=RequestTaskTrackingMiddleware(app,db)
            pending=asyncio.create_task(wrapper({'type':'http','method':'POST','path':'/api/v1/shipments/sync-route-status-from-dps','headers':[(b'x-youzi-task-id',b'example-task')]},receive,send))
            await asyncio.wait_for(entered.wait(), timeout=3)
            self.assertIn('example-task',active_ids())
            self.assertEqual(list_tasks(db)[0]['managedBy'],'request')
            release.set(); await pending
            self.assertNotIn('example-task',active_ids())
            self.assertEqual(list_tasks(db)[0]['state'],'failed')
            self.assertEqual(json.loads(sent[1]['body'])['updated'],4)
        asyncio.run(run())
        conn.close()
    def test_result_classification(self):
        task=complete({}, {'checked':2,'matched':1,'issues':[{'shipmentNo':'EXAMPLE','kind':'error','message':'no products'}]},200)
        self.assertEqual(task['resultKind'],'ctns')
        self.assertEqual(task['state'],'failed')
        self.assertTrue(task['finished'])
        self.assertEqual(complete({}, {'updated':2},200)['state'],'done')
        self.assertEqual(complete({}, {'skipped':True,'reason':'running'},200)['state'],'failed')
