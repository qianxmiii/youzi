"""DPS 港前标识：配置目录，远端成功后才回写本地。"""
import json
import re
import threading
import requests
from .shipment_query_config import load_config_json, resolve_dps_authorization
from ..db.shipment_order_status import PRE_PORT_STATUSES
from ..db.datetime_util import now_str
_lock=threading.Lock()
CONFIG_KEY='dps_commerce_waybill_mark'
DEFAULT_URL='https://logistics.worlddps.com/prod-api/tenant/order/commerceWaybillMark'

def migrate_legacy_catalog(database,path):
    """旧 JSON 目录只迁移一次，后续码表编辑/删除不被旧配置覆盖。"""
    if database is None or path is None: return
    from ..db.app_settings_table import get_setting,set_setting
    key='commerce_marks.catalog_migrated_v1'
    with database.lock:
        if get_setting(database.conn,key): return
        block=load_config_json(path).get(CONFIG_KEY) or {}
        if not isinstance(block,dict): raise ValueError('旧标识接口配置格式无效')
        legacy=block.get('marks',[])
        if not isinstance(legacy,list): raise ValueError('旧标识目录格式无效，请核对配置')
        try:
            for index,row in enumerate(legacy):
                if not isinstance(row,dict): raise ValueError('旧标识目录项目格式无效')
                code=str(row.get('id') or '').strip(); name=str(row.get('name') or '').strip(); color=str(row.get('color') or '#7c3aed')
                if not code or not name or not re.fullmatch(r'#[0-9A-Fa-f]{6}',color): raise ValueError('旧标识目录 ID、名称或颜色无效')
                database.conn.execute('INSERT OR IGNORE INTO commerce_mark_codes (code,name_zh,name_en,color,sort_order,is_active,created_time,updated_time) VALUES (?,?,?,?,?,1,?,?)',(code,name,'',color,index,now_str(),now_str()))
            set_setting(database.conn,key,'1')
            database.conn.commit()
        except Exception:
            database.conn.rollback()
            raise

def load_catalog(database, include_inactive=False):
    if database is None: return []
    with database.lock:
        rows=database.conn.execute("SELECT code,name_zh,color FROM commerce_mark_codes" + ("" if include_inactive else " WHERE is_active=1") + " ORDER BY sort_order,code").fetchall()
    return [{'id':r[0],'name':r[1],'color':r[2]} for r in rows]

def settings(path, database=None):
    migrate_legacy_catalog(database,path)
    config=load_config_json(path)
    block=config.get(CONFIG_KEY) or {}
    if not isinstance(block,dict): raise ValueError('标识接口配置应为对象')
    method=str(block.get('method') or 'PUT').strip().upper()
    if method not in ('PUT','POST'): raise ValueError('dps_commerce_waybill_mark.method 仅支持 PUT 或 POST')
    return {'url':str(block.get('url') or DEFAULT_URL),'method':method,'authorization':resolve_dps_authorization(config,block),'marks':load_catalog(database)}

def next_marks(current, selected, action):
    if action==0: return list(dict.fromkeys([*current,*selected]))
    if action==1: return [x for x in current if x not in selected]
    if action==2: return list(dict.fromkeys(selected))
    raise ValueError('操作类型无效')

def apply_marks(repo,path,ids,selected,action,task_id=''):
    if not ids or len(ids)>200: raise ValueError('请选择 1 至 200 票运单')
    if action not in (0,1,2) or (action in (0,1) and not selected): raise ValueError('请选择标识和有效操作')
    selected=list(dict.fromkeys(selected))
    cfg=settings(path,repo._database)
    allowed={m['id'] for m in cfg['marks']}
    if any(x not in allowed for x in selected): raise ValueError('标识不存在于配置目录')
    if not cfg['authorization']: raise ValueError('缺少 DPS 鉴权配置')
    if not _lock.acquire(blocking=False): raise ValueError('另一个标识操作正在执行，请稍后再试')
    try:
        rows=[]
        for item_id in dict.fromkeys(ids):
            row=repo.get_by_id(item_id)
            if not row or row.get('statusCode') not in PRE_PORT_STATUSES: raise ValueError('所选包含不存在或非港前运单，请刷新后重试')
            if not row.get('waybillId'): raise ValueError('所选运单缺少 DPS ID，请先更新运单')
            rows.append(row)
        events=[]
        if task_id:
            from ..db.task_history import record_event
            for row in rows:
                events.append(record_event(repo._database,task_id,row['shipmentNo'],{'marks':row.get('commerceMarks',[])},{'type':action,'markIds':selected}))
        try:
            response=requests.request(cfg.get('method','PUT'),cfg['url'],json={'type':action,'markIds':selected,'commerceWaybillIds':list(dict.fromkeys(r['waybillId'] for r in rows))},headers={'Authorization':cfg['authorization']},timeout=30)
            if response.status_code>=400: raise ValueError(f'DPS 标识操作失败 HTTP {response.status_code}')
            result=response.json()
            if not isinstance(result,dict) or result.get('code') not in (0,'0',200,'200'): raise ValueError('DPS 未确认标识操作成功，请核对远端结果')
        except requests.RequestException: raise ValueError('DPS 请求异常，结果可能已生效，请核对后再操作') from None
        except (TypeError,json.JSONDecodeError): raise ValueError('DPS 响应无效，请核对远端结果') from None
        database=repo._database
        with database.lock:
            try:
                for row in rows:
                    from ..db.shipment_marks import load_many_locked,replace_locked
                    current=load_many_locked(database.conn,[row['id']]).get(row['id'],[])
                    baseline=[m['id'] for m in current]
                    marks=next_marks(baseline,selected,action)
                    previous={m['id']:m for m in current}
                    known={m['id']:m for m in cfg['marks']}
                    labels=[known.get(key) or previous.get(key) or {'id':key,'name':key.removeprefix('name:'),'color':'#7c3aed'} for key in marks]
                    replace_locked(database.conn,row['id'],labels)
                    database.conn.execute('UPDATE shipments SET updated_time=? WHERE id=?',(now_str(),row['id']))
                database.conn.commit()
            except Exception:
                database.conn.rollback()
                raise ValueError('远端已成功，本地记录更新失败，请核对后刷新') from None
        if events:
            from ..db.task_history import finish_event
            for event in events: finish_event(database,event,{'ok':True,'message':'DPS 标识操作成功并已更新本地'})
        return {'total':len(rows),'updated':len(rows),'failed':0}
    finally: _lock.release()


def normalize_remote_marks(remote,catalog):
    params=remote.get('params')
    if isinstance(params,dict) and 'markVos' in params:
        values=params['markVos']
    elif 'markVos' in remote:
        values=remote['markVos']
    else:
        return None
    if values is None: values=[]
    if not isinstance(values,list): raise ValueError('markVos 不是数组')
    by_name={m['name']:m for m in catalog}
    marks=[]; seen=set()
    for value in values:
        if not isinstance(value,dict) or not str(value.get('name') or '').strip(): raise ValueError('markVos 缺少有效名称，保留本地标识')
        name=str(value['name']).strip()
        configured=by_name.get(name)
        key=configured['id'] if configured else 'name:'+name
        color=str(value.get('colour') or (configured or {}).get('color') or '#7c3aed')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',color): color='#7c3aed'
        if key not in seen: marks.append({'id':key,'name':name,'color':color}); seen.add(key)
    return marks


_sync_lock=threading.Lock()

def parse_mark_catalog(body):
    if not isinstance(body,dict) or body.get('code') not in (200,'200',0,'0'):
        raise ValueError('DPS 未确认标识查询成功')
    data=body.get('data')
    if not isinstance(data,list): raise ValueError('标识响应 data 应为数组，未更新码表')
    entries=[]; ids=set(); names=set()
    for row in data:
        if not isinstance(row,dict): raise ValueError('标识数据格式无效，未更新码表')
        key=str(row.get('id') or '').strip(); name=str(row.get('name') or '').strip()
        color=str(row.get('colour') or '#7c3aed').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',key) or not name or not re.fullmatch(r'#[0-9A-Fa-f]{6}',color):
            raise ValueError('标识 ID、名称或颜色无效，未更新码表')
        if key in ids or name in names: raise ValueError('远端标识 ID 或名称重复，未更新码表')
        ids.add(key); names.add(name)
        entries.append({'id':key,'name':name,'color':color})
    return entries

def sync_mark_catalog(database,path):
    if not _sync_lock.acquire(blocking=False): raise ValueError('正在同步标识，请稍后再试')
    try:
        config=load_config_json(path)
        block=config.get('dps_getMarks')
        if not isinstance(block,dict) or not str(block.get('url') or '').strip(): raise ValueError('请配置 dps_getMarks.url')
        method=str(block.get('method') or 'GET').strip().upper()
        if method not in ('GET','POST'): raise ValueError('dps_getMarks.method 仅支持 GET 或 POST')
        auth=resolve_dps_authorization(config,block)
        if not auth: raise ValueError('缺少 DPS 鉴权配置')
        try:
            response=requests.request(method,block['url'],headers={'Authorization':auth,'Accept':'application/json'},timeout=30)
            if response.status_code>=400: raise ValueError(f'查询标识失败 HTTP {response.status_code}，未更新码表')
            entries=parse_mark_catalog(response.json())
        except requests.RequestException: raise ValueError('标识查询网络异常，未更新码表，请稍后重试') from None
        except (json.JSONDecodeError,TypeError): raise ValueError('标识响应不是有效 JSON，未更新码表') from None
        created=updated=unchanged=0
        with database.lock:
            conn=database.conn
            existing={r['code']:dict(r) for r in conn.execute('SELECT code,name_zh,color FROM commerce_mark_codes')}
            # 先校验整个批次；不把名称冲突变成误合并或部分写入。
            owners={r['name_zh']:key for key,r in existing.items()}
            for item in entries:
                owner=owners.get(item['name'])
                if owner is not None and owner!=item['id']:
                    raise ValueError('标识名称与本地其他 ID 冲突，请先核对码表，未更新任何项目')
            try:
                now=now_str()
                for index,item in enumerate(entries):
                    old=existing.get(item['id'])
                    if old is None:
                        conn.execute('INSERT INTO commerce_mark_codes (code,name_zh,name_en,color,sort_order,is_active,created_time,updated_time) VALUES (?,?,?,?,?,1,?,?)',(item['id'],item['name'],'',item['color'],index,now,now))
                        created+=1
                    elif old['name_zh']!=item['name'] or old['color'].lower()!=item['color'].lower():
                        conn.execute('UPDATE commerce_mark_codes SET name_zh=?,color=?,updated_time=? WHERE code=?',(item['name'],item['color'],now,item['id']))
                        updated+=1
                    else: unchanged+=1
                conn.commit()
            except Exception:
                conn.rollback()
                raise ValueError('标识码表写入失败，已回滚本次同步') from None
        return {'total':len(entries),'created':created,'updated':updated,'unchanged':unchanged,'failed':0}
    finally: _sync_lock.release()
