"""明确点击启动的六步后台同步。只支持单后端进程，不依赖浏览器请求存活。"""
from __future__ import annotations

from datetime import datetime
import copy
import json
from pathlib import Path
import re
import threading
import time
import uuid

import requests

from ..db.task_history import save_task
from . import sync_coordination as coordination
from .shipment_query_config import (
    load_config_json, resolve_dps_authorization, _normalize_dps_authorization, update_logistics_config,
    build_shipment_query_by_person_url, resolve_transit_time_range,
)

STEPS = (
    ('pickup', '提货中运单'), ('warehoused', '已入仓运单'), ('transit', '在途运单'),
    ('internal', '内部轨迹'), ('carrier', '承运商轨迹'), ('route', '明细状态'),
)
ACTIVE = {'queued', 'running'}
TERMINAL = {'done', 'partial', 'waiting_authorization', 'interrupted'}


def validate_authorization(config, authorization):
    """只读探测第一条记录，要求明确成功且结构可用；不持久化响应。"""
    block = config.get('shipment_queryByPerson') or {}
    url = str(block.get('url') or '').strip()
    if not url.startswith(('http://', 'https://')):
        raise ValueError('请先配置 DPS 在途查询地址')
    url = build_shipment_query_by_person_url(url, page_num=1, time_range='none')
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
    parsed = urlparse(url)
    pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != 'pagesize']
    url = urlunparse(parsed._replace(query=urlencode([*pairs, ('pageSize', '1')])))
    try:
        response = requests.get(url, headers={'Authorization': authorization, 'Accept': 'application/json'},
                                timeout=12, allow_redirects=False)
        coordination.check_dps_response(response)
        if response.status_code != 200:
            raise ValueError('授权验证未成功（HTTP 非成功响应），未保存或启动')
        body = response.json()
        coordination.check_dps_response(response, body)
        if not isinstance(body, dict) or str(body.get('code')) != '200' or not isinstance(body.get('rows'), list):
            raise ValueError('授权验证未返回有效运单列表，未保存或启动')
    except coordination.DpsAuthorizationExpired:
        raise ValueError('DPS 授权无效，未保存或启动') from None
    except (requests.RequestException, json.JSONDecodeError):
        raise ValueError('授权验证网络异常或响应无法解析，未保存或启动') from None


def save_authorization(path: Path, authorization: str, key: str = 'dps_authorization'):
    if key not in ('dps_authorization', 'dps_ddlz_authorization'):
        raise ValueError('不支持的授权配置项')
    update_logistics_config(path, lambda config: config.update({key: authorization}))


class DailySyncManager:
    def __init__(self, database, config_path, runners, *, validator=validate_authorization,
                 launch=None):
        self.db, self.path, self.runners = database, Path(config_path), runners
        self.validator = validator
        self.launch = launch or (lambda fn: threading.Thread(target=fn, daemon=True, name='youzi-daily-sync').start())
        self.lock = threading.RLock()
        with database.lock:
            database.conn.execute('CREATE TABLE IF NOT EXISTS daily_sync_runs (id TEXT PRIMARY KEY, started INTEGER NOT NULL, payload TEXT NOT NULL)')
            database.conn.commit()
        # 在应用启动时创建唯一 manager；上个进程的未结束任务不得永久显示运行中。
        with database.lock:
            rows = database.conn.execute('SELECT payload FROM daily_sync_runs').fetchall()
        for row in rows:
            run = json.loads(row[0])
            if run['status'] in ACTIVE:
                run['status'] = 'interrupted'
                run['message'] = '后端已重启，本轮中断；继续时重新核对未完成步骤'
                for step in run['steps']:
                    if step['status'] == 'running':
                        step.update(status='partial', message='后端已重启，该步骤需继续核对')
                self._persist(run)

    def _load(self, run_id):
        with self.db.lock:
            row = self.db.conn.execute('SELECT payload FROM daily_sync_runs WHERE id=?', (run_id,)).fetchone()
        if row is None:
            raise ValueError('未找到每日同步任务')
        return json.loads(row[0])

    def latest(self):
        with self.db.lock:
            row = self.db.conn.execute('SELECT id FROM daily_sync_runs ORDER BY started DESC, rowid DESC LIMIT 1').fetchone()
        return self.public(self._load(row[0])) if row else None

    def configured(self):
        try:
            cfg = load_config_json(self.path)
            return bool(resolve_dps_authorization(cfg, cfg.get('shipment_queryByPerson')))
        except (OSError, ValueError):
            return False

    @staticmethod
    def public(run):
        data = copy.deepcopy(run)
        for step in data['steps']:
            if 'candidates' in step:
                step['candidateCount'] = len(step['candidates'])
                step['completedCount'] = len(step.get('completed', []))
                step['pendingCount'] = step['candidateCount'] - step['completedCount']
            step.pop('candidates', None)
            step.pop('completed', None)
        return data

    def _persist(self, run):
        with self.db.lock:
            self.db.conn.execute('INSERT INTO daily_sync_runs VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                                 (run['id'], run['started'], json.dumps(run, ensure_ascii=False)))
            self.db.conn.commit()
        public = self.public(run)
        success = sum(s['status'] == 'done' for s in run['steps'])
        lines = [run['message']]
        for s in public['steps']:
            lines.append(f"{s['label']}：{s['status']}；{s.get('message', '')}")
        save_task(self.db, {
            'id': run['id'], 'title': '每日同步', 'started': run['started'],
            'state': 'running' if run['status'] in ACTIVE else ('done' if run['status'] == 'done' else 'failed'),
            'finished': None if run['status'] in ACTIVE else int(time.time() * 1000),
            'managedBy': 'server', 'source': '计划任务', 'sourcePath': '/scheduled-tasks',
            'resumable': run['status'] not in ('done', 'closed'),
            'message': run['message'], 'details': '\n'.join(lines),
            'stats': [{'label': '已完成步骤', 'value': success}, {'label': '总步骤', 'value': 6}],
            'rows': [{'shipmentNo': '—', 'message': f"{s['label']}：{s.get('message', s['status'])}"} for s in public['steps']],
        })

    def start(self, authorization='', *, resume_id=None, start=None, end=None):
        # reserve 跨请求线程持有；worker 通过 lease 继承，堵住验证/保存与任务启动的竞态。
        owner = coordination.reserve()
        saved = False
        try:
            with self.lock:
                latest = self.latest()
                if latest and latest['status'] not in ('done', 'closed') and not resume_id:
                    raise ValueError('已有未完成每日同步，请继续该任务')
                run = self._load(resume_id) if resume_id else None
                if run and (run['status'] not in TERMINAL or run['status'] == 'done'):
                    raise ValueError('该任务不能继续')
                if run and latest and latest['id'] != run['id']:
                    raise ValueError('只能继续最近一轮任务')
                config = load_config_json(self.path)
                auth = _normalize_dps_authorization(authorization) if authorization.strip() else resolve_dps_authorization(config, config.get('shipment_queryByPerson'))
                if not auth or len(auth) > 16384 or '\n' in auth or '\r' in auth:
                    raise ValueError('请输入有效的 DPS Authorization')
                self.validator(config, auth)
                if run is None:
                    start, end = resolve_transit_time_range(start, end)
                    if datetime.fromisoformat(start) > datetime.fromisoformat(end):
                        raise ValueError('开始日期不能晚于结束日期')
                if authorization.strip():
                    save_authorization(self.path, auth)
                    saved = True
                if run is None:
                    run = {'id': str(uuid.uuid4()), 'started': int(time.time() * 1000),
                           'start': start, 'end': end, 'steps': [
                               {'key': k, 'label': label, 'status': 'pending', 'attempt': 0} for k, label in STEPS]}
                run.update(status='queued', message='已验证授权，等待开始六步同步')
                self._persist(run)
                result = self.public(run)
                result['authorizationSaved'] = saved
                try:
                    self.launch(lambda: self._execute(run, owner, auth))
                except Exception:
                    run.update(status='interrupted', message='后台任务启动失败，请继续本轮任务')
                    self._persist(run)
                    raise
                return result
        except (ValueError, coordination.SyncBusy):
            coordination.release(owner)
            raise
        except Exception:
            coordination.release(owner)
            raise ValueError('授权已保存，但任务启动失败，请核对后继续' if saved else '配置读取、保存或任务创建失败，未启动同步') from None

    def close(self, run_id):
        owner = coordination.reserve()
        try:
            with self.lock:
                run = self._load(run_id)
                if run['status'] not in ('partial', 'waiting_authorization', 'interrupted'):
                    raise ValueError('只能结束已暂停、部分完成或中断的任务')
                run.update(status='closed', message='本轮已结束，未完成结果已保留；不代表全部同步成功')
                self._persist(run)
                return self.public(run)
        finally:
            coordination.release(owner)

    def _execute(self, run, owner, auth):
        def clean(text):
            text = str(text).replace(auth, '[已隐藏授权]').replace(auth.removeprefix('Bearer '), '[已隐藏授权]')
            text = re.sub(r'(?i)(bearer|basic)\s+[^\s"\',;]+', r'\1 [已隐藏授权]', text)
            return text[:1500]

        try:
            with coordination.lease(owner):
                run.update(status='running', message='开始每日同步')
                self._persist(run)
                for step in run['steps']:
                    if step['status'] == 'done':
                        continue
                    step.update(status='running', attempt=step['attempt'] + 1, started=int(time.time() * 1000))
                    step['message'] = '重新核对未完成列表步骤并去重落库' if step['attempt'] > 1 and step['key'] in ('pickup', 'warehoused', 'transit') else '处理中'
                    run['message'] = f"正在更新：{step['label']}"
                    self._persist(run)
                    ctx = _Runtime(step, lambda: self._persist(run), clean)
                    token = coordination.runtime.set(ctx)
                    try:
                        result = self.runners[step['key']](run['start'], run['end'], ctx.log)
                        stats = {k: v for k, v in result.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
                        step['stats'] = stats
                        pending = len(set(step.get('candidates', [])) - set(step.get('completed', [])))
                        bad = (bool(result.get('error') or result.get('errors') or result.get('failed') or pending)
                               or result.get('skipped') is True or result.get('intervalSkipped') is True
                               or int(result.get('remoteTotal', 0)) > int(result.get('total', 0)))
                        step['status'] = 'partial' if bad else 'done'
                        labels = {'total':'本次候选', 'created':'新增', 'updated':'更新', 'unchanged':'无变化',
                                  'skipped':'跳过/无变化', 'empty':'无轨迹', 'failed':'失败', 'notFound':'未返回/未匹配'}
                        step['message'] = '；'.join(f'{label} {stats[k]}' for k, label in labels.items() if k in stats)
                        issues = [result.get('error'), result.get('reason'), *(result.get('errors') or [])]
                        step['errors'] = [clean(x) for x in issues if x][:20]
                        if pending:
                            step['message'] += f'；待补查 {pending}'
                    except coordination.DpsAuthorizationExpired:
                        step.update(status='partial', message='DPS 授权失效，更新后继续', finished=int(time.time() * 1000))
                        run.update(status='waiting_authorization', message='DPS 授权失效，已暂停；请更新授权后继续')
                        self._persist(run)
                        return
                    except Exception as exc:
                        if step.get('candidates') and set(step['candidates']) <= set(step.get('completed', [])):
                            # 行写入后的衍生计算失败：重查该阶段，不能用零候选跳过收尾。
                            step['completed'] = []
                        step.update(status='partial', message='该步骤未完成，可继续补查', errors=[clean(exc)])
                    finally:
                        coordination.runtime.reset(token)
                        step['finished'] = int(time.time() * 1000)
                    self._persist(run)
                good = all(s['status'] == 'done' for s in run['steps'])
                run.update(status='done' if good else 'partial',
                           message='六步每日同步已完成' if good else '本轮部分完成，请查看未完成步骤并继续补查')
                self._persist(run)
        except BaseException:
            run.update(status='interrupted', message='本轮执行中断，请继续未完成步骤')
            self._persist(run)
        finally:
            coordination.release(owner)


class _Runtime:
    def __init__(self, step, save, clean):
        self.step, self.save, self.clean = step, save, clean
        self.retry = False
        self.last_save = 0.0

    def log(self, text):
        # 不保存整个远程返回报文。仅保留一条脱敏进度，限频写入任务中心。
        self.step['message'] = self.clean(text)
        if time.monotonic() - self.last_save > 1:
            self.last_save = time.monotonic()
            self.save()
