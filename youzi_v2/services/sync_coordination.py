"""同一后端进程的同步租约，以及每日任务的候选集/检查点上下文。"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import threading
import uuid
from fastapi import HTTPException

_lock = threading.Lock()
_owner: str | None = None
_context: ContextVar[str | None] = ContextVar('sync_lease', default=None)
runtime: ContextVar[object | None] = ContextVar('daily_sync_runtime', default=None)


class SyncBusy(HTTPException):
    def __init__(self):
        super().__init__(409, '已有同步任务运行中，请等待完成后再执行')


class DpsAuthorizationExpired(RuntimeError):
    def __init__(self):
        super().__init__('DPS 授权已失效，请更新授权后继续')


def reserve() -> str:
    global _owner
    with _lock:
        if _owner is not None:
            raise SyncBusy()
        _owner = str(uuid.uuid4())
        return _owner


def release(owner: str):
    global _owner
    with _lock:
        if _owner == owner:
            _owner = None


@contextmanager
def lease(owner: str):
    token = _context.set(owner)
    try:
        yield
    finally:
        _context.reset(token)


def serialized_sync(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with _lock:
            nested = _owner is not None and _context.get() == _owner
        if nested:
            return fn(*args, **kwargs)
        try:
            owner = reserve()
        except SyncBusy:
            if kwargs.get('trigger') == 'scheduled':
                # 不让占用中的每日任务打断整轮调度（其他不相关定时任务仍可执行）。
                return {'skipped': True, 'reason': '每日或其他同步运行中，本次定时同步跳过',
                        'intervalSkipped': True, 'skipReason': '每日或其他同步运行中',
                        'total': 0, 'created': 0, 'updated': 0, 'failed': 0}
            raise
        try:
            with lease(owner):
                return fn(*args, **kwargs)
        finally:
            release(owner)
    return wrapped


def check_dps_response(response, body=None):
    """仅 DPS 调用点使用。403/超时/承运商错误不能等同授权失效。"""
    code = body.get('code') if isinstance(body, dict) else None
    if response.status_code == 401 or str(code) == '401':
        raise DpsAuthorizationExpired()


def pending_rows(load, key):
    """load(None) 保持既有全量资格；续跑按初始候选取当前行，仍走全量合并模式。"""
    ctx = runtime.get()
    if ctx is None:
        return load(None)
    ids = ctx.step.get('candidates')
    if ids is None:
        rows = load(None)
        ctx.step['candidates'] = [key(row) for row in rows]
        ctx.save()
    else:
        rows = load(ids) if ids else []
    done = set(ctx.step.get('completed', []))
    # 未找到的原始候选保留为待处理，不能把缺失行悄悄算成功。
    return [row for row in rows if key(row) not in done]


def retry_item():
    ctx = runtime.get()
    if ctx is not None:
        ctx.retry = True


def checkpointed_rows(rows, key):
    ctx = runtime.get()
    for row in rows:
        if ctx is not None:
            ctx.retry = False
        yield row
        if ctx is not None and not ctx.retry:
            sn = key(row)
            completed = ctx.step.setdefault('completed', [])
            if sn not in completed:
                completed.append(sn)
            ctx.save()
