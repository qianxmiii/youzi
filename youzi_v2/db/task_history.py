"""持久任务摘要与批量更新审计；业务数据仅存本地数据库。"""
import json
from .datetime_util import now_str

def ensure_schema(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS task_history_deleted (id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS task_history (id TEXT PRIMARY KEY, started INTEGER NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_history_started ON task_history(started DESC)")
    conn.execute("CREATE TABLE IF NOT EXISTS task_operation_events (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, shipment_no TEXT NOT NULL, recorded_at TEXT NOT NULL, before_json TEXT NOT NULL, after_json TEXT NOT NULL, result_json TEXT NOT NULL)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_operation_events(task_id, id)")

def save_task(database, task):
    with database.lock:
        if database.conn.execute("SELECT 1 FROM task_history_deleted WHERE id=?", (task["id"],)).fetchone():
            return
        database.conn.execute("INSERT INTO task_history VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at", (task['id'], task['started'], json.dumps(task, ensure_ascii=False), now_str()))
        database.conn.commit()

def list_tasks(database, limit=50, offset=0):
    with database.lock:
        rows = database.conn.execute("SELECT payload FROM task_history ORDER BY started DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    return [json.loads(row[0]) for row in rows]

def record_event(database, task_id, shipment_no, before, after):
    with database.lock:
        cur = database.conn.execute("INSERT INTO task_operation_events (task_id,shipment_no,recorded_at,before_json,after_json,result_json) VALUES (?,?,?,?,?,?)", (task_id,shipment_no,now_str(),json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False),'{}'))
        database.conn.commit()
        return cur.lastrowid

def finish_event(database, event_id, result):
    with database.lock:
        database.conn.execute("UPDATE task_operation_events SET result_json=? WHERE id=?", (json.dumps(result,ensure_ascii=False),event_id))
        database.conn.commit()

def list_events(database, task_id):
    with database.lock:
        rows = database.conn.execute("SELECT shipment_no, recorded_at, before_json, after_json, result_json FROM task_operation_events WHERE task_id=? ORDER BY id", (task_id,)).fetchall()
    return [{'shipmentNo':r[0], 'recordedAt':r[1], 'before':json.loads(r[2]), 'after':json.loads(r[3]), 'result':json.loads(r[4])} for r in rows]


def delete_task(database, task_id):
    """真正删除任务和关联操作明细，墓碑阻止延迟快照重新生成记录。"""
    with database.lock:
        row = database.conn.execute('SELECT payload FROM task_history WHERE id=?',(task_id,)).fetchone()
        if row is None: raise KeyError(task_id)
        if json.loads(row[0]).get('state') == 'running':
            raise ValueError('运行中或结果待确认的记录不能删除，可先核对结果')
        try:
            database.conn.execute('INSERT OR IGNORE INTO task_history_deleted VALUES (?)',(task_id,))
            database.conn.execute('DELETE FROM task_operation_events WHERE task_id=?',(task_id,))
            database.conn.execute('DELETE FROM task_history WHERE id=?',(task_id,))
            database.conn.commit()
        except Exception:
            database.conn.rollback()
            raise
