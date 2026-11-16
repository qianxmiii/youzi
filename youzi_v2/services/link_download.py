"""受支持站点的文件下载规则、持久任务及打包。"""
from __future__ import annotations
import json
import re
import shutil
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qs
import requests
from ..db.task_history import save_task

RETENTION_SEC = 7 * 86400
MAX_FILE = 50 * 1024 * 1024
MAX_TOTAL = 500 * 1024 * 1024
_active: set[str] = set()
_lock = threading.Lock()
# 每个规则独立匹配与转换，新增站点无需修改任务流程。
RULES = [{'id':'pickup-photo','name':'提货照片','host':'pickupphoto.nextsls.com','port':30233,'paths':('/photo/image','/photo/image/pack')}]

def ensure_schema(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS link_download_jobs (id TEXT PRIMARY KEY, created REAL NOT NULL, payload TEXT NOT NULL)")

def resolve_link(raw):
    text = raw.strip().replace('\\:', ':')
    try:
        url = urlsplit(text)
        if url.username or url.password or url.fragment or url.scheme not in ('http','https'):
            raise ValueError()
        rule = next((r for r in RULES if url.hostname == r['host'] and url.port == r['port'] and url.path in r['paths']), None)
        if not rule or not parse_qs(url.query).get('id', [''])[0].strip():
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('暂不支持此链接，请使用提货照片查看链接（包含 id）') from None
    view = urlunsplit((url.scheme,url.netloc,rule['paths'][0],url.query,''))
    download = urlunsplit((url.scheme,url.netloc,rule['paths'][1],url.query,''))
    return view, download, rule['name']

def validate_rows(rows):
    if not 1 <= len(rows) <= 100:
        raise ValueError('每批请填写 1 至 100 票')
    seen = set()
    out = []
    for row in rows:
        no = row['shipmentNo'].strip()
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', no) or no.upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
            raise ValueError('运单号仅支持字母、数字、横线及下划线，最长 80 字符')
        if no.casefold() in seen:
            raise ValueError('存在重复运单号，请先合并或删除重复行')
        seen.add(no.casefold())
        view, download, rule = resolve_link(row['url'])
        out.append({'shipmentNo':no,'url':view,'downloadUrl':download,'rule':rule,'status':'waiting','message':'等待下载'})
    return out

def _save(db, job):
    with db.lock:
        db.conn.execute('INSERT INTO link_download_jobs VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (job['id'],job['created'],json.dumps(job,ensure_ascii=False)))
        db.conn.commit()
    done = sum(r['status'] in ('success','failed') for r in job['rows'])
    success = sum(r['status']=='success' for r in job['rows'])
    failed = sum(r['status']=='failed' for r in job['rows'])
    running = job['status']=='running'
    save_task(db, {'id':job['id'],'title':'链接批量下载 · 提货照片','started':int(job['created']*1000),'state':'running' if running else 'failed' if failed or job['status']=='failed' else 'done','progress':round(done/len(job['rows'])*100),'message':f"已处理 {done}/{len(job['rows'])} · 成功 {success} · 失败 {failed}" + (' · 后端中断，请核对并重试' if job.get('interrupted') else ''),'details':'\n'.join(f"{r['shipmentNo']}：{r['message']}" for r in job['rows']),'rows':[{'shipmentNo':r['shipmentNo'],'message':r['message']} for r in job['rows']],'source':'链接批量下载','sourcePath':'/tools/link-download','managedBy':'server','href':f"/tools/link-download?job={job['id']}", **({'finished':int(job['finished']*1000)} if job.get('finished') else {})})

def get_job(db, job_id):
    with db.lock:
        row = db.conn.execute('SELECT payload FROM link_download_jobs WHERE id=?',(job_id,)).fetchone()
    if not row:
        raise KeyError(job_id)
    job = json.loads(row[0])
    with _lock:
        active = job_id in _active
    if job['status']=='running' and not active:
        job['status']='failed'; job['interrupted']=True; job['finished']=time.time()
        for item in job['rows']:
            if item['status'] in ('waiting','running'):
                item.update(status='failed',message='后端服务中断，请重试')
        _save(db,job)
    job['expired'] = time.time()-job['created'] > RETENTION_SEC
    return job

def list_jobs(db):
    with db.lock:
        ids = [r[0] for r in db.conn.execute('SELECT id FROM link_download_jobs ORDER BY created DESC LIMIT 50')]
    return [get_job(db,i) for i in ids]

def _fetch(item, folder, budget, budget_lock):
    target = folder / (item['shipmentNo']+'.zip')
    for attempt in range(2):
        try:
            with requests.Session() as session:
                session.trust_env = False
                with session.get(item['downloadUrl'],stream=True,timeout=(10,45),allow_redirects=False) as response:
                    if response.status_code != 200:
                        raise ValueError(f'下载失败 HTTP {response.status_code}（不跟随重定向）')
                    if 'text/' in response.headers.get('Content-Type','').lower():
                        raise ValueError('链接返回网页而非压缩包')
                    size = 0
                    started = time.monotonic()
                    with target.open('wb') as output:
                        for chunk in response.iter_content(65536):
                            size += len(chunk)
                            with budget_lock:
                                budget[0] += len(chunk)
                                total = budget[0]
                            if size > MAX_FILE or total > MAX_TOTAL or time.monotonic()-started > 180:
                                raise ValueError('文件过大或下载超时，单票上限 50MB、批次上限 500MB')
                            output.write(chunk)
            if not zipfile.is_zipfile(target):
                raise ValueError('返回内容不是有效 ZIP 压缩包')
            return {'status':'success','message':'下载成功','filename':target.name}
        except requests.RequestException:
            if attempt == 0:
                continue
            return {'status':'failed','message':'连接失败或超时，请稍后重试'}
        except (ValueError,OSError) as exc:
            return {'status':'failed','message':str(exc) if isinstance(exc,ValueError) else '本地文件写入失败'}
    return {'status':'failed','message':'下载失败'}

def _run(db, root, job):
    try:
        folder = root / job['id']
        folder.mkdir(parents=True,exist_ok=True)
        budget, budget_lock = [0], threading.Lock()
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(_fetch,item,folder,budget,budget_lock):item for item in job['rows']}
            for future in as_completed(futures):
                futures[future].update(future.result())
                _save(db,job)
        successful = [r for r in job['rows'] if r['status']=='success']
        if successful:
            with zipfile.ZipFile(folder/'bundle.zip','w',compression=zipfile.ZIP_STORED) as archive:
                for row in successful:
                    archive.write(folder/row['filename'],row['filename'])
        job['status']='done'; job['finished']=time.time()
        _save(db,job)
    except Exception:
        job['status']='failed'; job['finished']=time.time()
        for row in job['rows']:
            if row['status']=='waiting': row.update(status='failed',message='任务处理异常，请重试')
        _save(db,job)
    finally:
        with _lock: _active.discard(job['id'])

def purge_expired_files(db, root):
    """只清理本工具目录下、数据库登记且超过保留期的 UUID 子目录。"""
    base = root.resolve()
    with db.lock:
        expired = db.conn.execute('SELECT id FROM link_download_jobs WHERE created < ?', (time.time()-RETENTION_SEC,)).fetchall()
    for (job_id,) in expired:
        try:
            if str(uuid.UUID(job_id)) != job_id:
                continue
            target = root / job_id
            if target.is_symlink() or target.resolve().parent != base:
                continue
            with _lock:
                if job_id in _active:
                    continue
            if target.is_dir():
                shutil.rmtree(target)
        except (ValueError,OSError):
            # 文件正被下载或无权限时保留，下次创建任务再尝试。
            continue


def create_job(db, root: Path, rows):
    items = validate_rows(rows)
    purge_expired_files(db, root)
    with _lock:
        if len(_active)>=2: raise ValueError('已有两个下载批次运行中，请稍后再试')
        job = {'id':str(uuid.uuid4()),'created':time.time(),'status':'running','rows':items}
        _active.add(job['id'])
    try:
        _save(db,job)
        threading.Thread(target=_run,args=(db,root,job),daemon=True,name='link-download-'+job['id'][:8]).start()
    except Exception:
        with _lock: _active.discard(job['id'])
        raise
    return job

def download_path(db, root, job_id, index=None):
    job = get_job(db,job_id)
    if job['expired']: raise ValueError('下载文件已过期，请重新创建任务')
    if index is None:
        if job['status']=='running': raise ValueError('任务尚未完成')
        filename, display = 'bundle.zip', '照片下载_'+job['id'][:8]+'.zip'
    else:
        if index<0 or index>=len(job['rows']) or job['rows'][index]['status']!='success': raise ValueError('该票尚未下载成功')
        filename = display = job['rows'][index]['filename']
    path = root / job['id'] / filename
    if not path.is_file(): raise ValueError('没有可下载文件，请重试失败项或重新下载')
    return path,display
