"""为手动同步请求记录实际服务端生命周期；不改变请求及响应内容。"""
import json
import threading
import time
from ..db.task_history import save_task

PATHS = {'/api/v1/commerce-marks/sync','/api/v1/commerce-marks','/api/v1/shipment-remarks','/api/v1/shipments/sync-tracking','/api/v1/shipments/sync-carrier-tracking','/api/v1/shipments/sync-from-dps','/api/v1/shipments/sync-preport-from-dps','/api/v1/shipments/sync-today-from-dps','/api/v1/shipments/sync-today-transit-from-dps','/api/v1/shipments/sync-route-status-from-dps','/api/v1/shipments/check-order-product-ctns'}
_active = set()
_lock = threading.Lock()

def active_ids():
    with _lock: return list(_active)

def complete(task, body, status):
    data = body if isinstance(body,dict) else {}
    labels = {'total':'总票数','created':'新增','updated':'已更新','unchanged':'无变化','failed':'失败','notFound':'未找到','checked':'已核对','matched':'件数一致','logCount':'轨迹条数'}
    stats = [{'label':label,'value':data[key]} for key,label in labels.items() if isinstance(data.get(key),(int,float))]
    errors = [str(x) for x in data.get('errors',[]) if x] if isinstance(data.get('errors'),list) else []
    for key in ('error','detail'):
        if data.get(key): errors.append(str(data[key]))
    if data.get('skipped') is True: errors.append(str(data.get('reason') or '任务已跳过'))
    steps = data.get('steps',[]) if isinstance(data.get('steps'),list) else []
    for step in steps:
        if step.get('error') or step.get('skipped'): errors.append(str(step.get('label',''))+'：'+str(step.get('error') or step.get('reason') or '已跳过'))
    if steps:
        stats += [{'label':labels[key],'value':sum(s.get(key,0) or 0 for s in steps)} for key in ('created','updated','failed')]
    issues = data.get('issues',[]) if isinstance(data.get('issues'),list) else []
    if 'issues' in data:
        task['resultKind']='ctns'
        stats += [{'label':'件数不一致','value':sum(r.get('kind')=='mismatch' for r in issues)},{'label':'查询异常','value':sum(r.get('kind')!='mismatch' for r in issues)}]
    task['rows'] = issues or [{'shipmentNo':'—','message':error} for error in errors]
    task['stats']=stats
    bad = status>=400 or bool(errors or issues or data.get('failed')) or any(s.get('failed') for s in steps)
    task.update(state='failed' if bad else 'done',finished=int(time.time()*1000),progress=100)
    task['message']=' · '.join(f"{s['label']} {s['value']}" for s in stats) or ('请求失败' if bad else '处理完成')
    task['details']='\n'.join([task['message'],*errors,*[str(r.get('shipmentNo',''))+'：'+str(r.get('message') or '件数不一致') for r in issues],*[str(s.get('label',''))+'：新增 '+str(s.get('created',0))+'，更新 '+str(s.get('updated',0)) for s in steps]])
    return task

class RequestTaskTrackingMiddleware:
    def __init__(self, app, database): self.app,self.database=app,database
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope.get('method')!='POST' or scope.get('path') not in PATHS:
            return await self.app(scope,receive,send)
        headers=dict(scope.get('headers',[]))
        task_id=headers.get(b'x-youzi-task-id',b'').decode('ascii',errors='ignore')
        with self.database.lock:
            row=self.database.conn.execute('SELECT payload FROM task_history WHERE id=?',(task_id,)).fetchone() if task_id else None
        if not row: return await self.app(scope,receive,send)
        task=json.loads(row[0])
        task.update(managedBy='request',state='running')
        with _lock: _active.add(task_id)
        save_task(self.database,task)
        chunks=[]; size=0; response_status=500
        async def capture(message):
            nonlocal response_status,size
            if message['type']=='http.response.start': response_status=message['status']
            if message['type']=='http.response.body':
                body=message.get('body',b''); size+=len(body)
                if size<=2000000: chunks.append(body)
            await send(message)
        try:
            await self.app(scope,receive,capture)
            try: body=json.loads(b''.join(chunks)) if size<=2000000 else {'error':'结果较大，请在对应功能中查看'}
            except (ValueError,UnicodeError): body={'error':'未取得完整结果，请核对'}
            save_task(self.database,complete(task,body,response_status))
        except BaseException:
            task.update(state='failed',finished=int(time.time()*1000),message='请求中断，执行结果需核对',details='请核对当前数据后再决定是否重试。')
            save_task(self.database,task)
            raise
        finally:
            with _lock: _active.discard(task_id)
