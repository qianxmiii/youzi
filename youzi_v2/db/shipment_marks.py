"""运单标识关联：以关联表为读写来源，旧 JSON 仅用于一次性回填。"""
import json
from .datetime_util import now_str

def normalize_items(marks):
    out=[];seen=set()
    for mark in marks:
        if not isinstance(mark,dict): raise ValueError('标识格式无效')
        name=str(mark.get('name') or '').strip(); key=str(mark.get('id') or '').strip()
        if not name: raise ValueError('标识名称不能为空')
        mark_id=key if key and not key.startswith('name:') else None
        identity=mark_id or 'name:'+name
        if identity not in seen:
            out.append((identity,mark_id,name,str(mark.get('color') or '#7c3aed')));seen.add(identity)
    return out

def replace_locked(conn,shipment_id,marks):
    items=normalize_items(marks)
    conn.execute('DELETE FROM shipment_marks WHERE shipment_id=?',(shipment_id,))
    conn.executemany('INSERT INTO shipment_marks (shipment_id,mark_key,mark_id,remote_name,remote_color,sort_order,synced_at) VALUES (?,?,?,?,?,?,?)',[(shipment_id,key,mark_id,name,color,index,now_str()) for index,(key,mark_id,name,color) in enumerate(items)])

def load_many_locked(conn,ids):
    if not ids:return {}
    result={key:[] for key in ids}
    # 未匹配的名称可以在码表补齐后直接解析成 ID，不丢弃未知标识。
    rows=conn.execute('SELECT m.shipment_id,COALESCE(m.mark_id,c.code) AS resolved_id,m.remote_name,m.remote_color FROM shipment_marks m LEFT JOIN commerce_mark_codes c ON m.mark_id IS NULL AND c.name_zh=m.remote_name WHERE m.shipment_id IN ('+','.join('?' for _ in ids)+') ORDER BY m.shipment_id,m.sort_order,m.mark_key',ids).fetchall()
    for row in rows:
        result[row[0]].append({'id':row[1] or 'name:'+row[2],'name':row[2],'color':row[3]})
    return result

def filter_sql(keys):
    keys=list(dict.fromkeys(keys))
    placeholders=','.join('?' for _ in keys)
    names=[key.removeprefix('name:') for key in keys if key.startswith('name:')]
    sql='EXISTS (SELECT 1 FROM shipment_marks sm WHERE sm.shipment_id=s.id AND (sm.mark_id IN ('+placeholders+') OR (sm.mark_id IS NULL AND sm.remote_name IN (SELECT name_zh FROM commerce_mark_codes WHERE code IN ('+placeholders+')))'
    params=[*keys,*keys]
    if names:
        sql+=' OR (sm.mark_id IS NULL AND sm.remote_name IN ('+','.join('?' for _ in names)+'))';params.extend(names)
    return sql+'))',params

def ensure_schema(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS shipment_marks (shipment_id TEXT NOT NULL, mark_key TEXT NOT NULL, mark_id TEXT, remote_name TEXT NOT NULL, remote_color TEXT NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0, synced_at TEXT NOT NULL, PRIMARY KEY(shipment_id,mark_key), FOREIGN KEY(shipment_id) REFERENCES shipments(id) ON DELETE CASCADE)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_shipment_marks_mark ON shipment_marks(mark_id,shipment_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_shipment_marks_name ON shipment_marks(remote_name,shipment_id) WHERE mark_id IS NULL')
    from .app_settings_table import get_setting,set_setting
    migration='shipment_marks.relation_migrated_v1'
    if get_setting(conn,migration):return
    conn.execute('SAVEPOINT migrate_shipment_marks')
    try:
        catalog={row[0]:{'name':row[1],'color':row[2]} for row in conn.execute('SELECT code,name_zh,color FROM commerce_mark_codes')}
        by_name={row['name']:key for key,row in catalog.items()}
        for row in conn.execute('SELECT id,commerce_mark_ids,commerce_marks FROM shipments'):
            ids=json.loads(row[1] or '[]');marks=json.loads(row[2] or '[]')
            if not isinstance(ids,list) or not isinstance(marks,list):raise ValueError('旧标识快照格式无效，迁移未完成')
            represented=set()
            for mark in marks:
                key=str(mark.get('id') or '')
                if not key or key.startswith('name:'): key=by_name.get(mark.get('name'),key or 'name:'+str(mark.get('name') or ''))
                mark['id']=key;represented.add(key)
            for key in ids:
                resolved=by_name.get(key.removeprefix('name:'),key) if key.startswith('name:') else key
                if resolved not in represented:
                    meta=catalog.get(resolved,{})
                    marks.append({'id':resolved,'name':meta.get('name') or key.removeprefix('name:'),'color':meta.get('color') or '#7c3aed'})
            # 只回填尚无关联行的运单，重复启动不会覆盖新数据。
            if marks and not conn.execute('SELECT 1 FROM shipment_marks WHERE shipment_id=?',(row[0],)).fetchone():replace_locked(conn,row[0],marks)
        set_setting(conn,migration,'1')
        conn.execute('RELEASE SAVEPOINT migrate_shipment_marks')
    except Exception:
        conn.execute('ROLLBACK TO SAVEPOINT migrate_shipment_marks');conn.execute('RELEASE SAVEPOINT migrate_shipment_marks');raise
