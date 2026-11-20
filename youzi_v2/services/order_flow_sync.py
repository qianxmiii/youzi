"""拉取订单流转并写入本地快照。失败时不把已有订单标成已结束。"""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

from ..db.connection import Database
from ..db.datetime_util import now_str
from ..db.order_flow_repository import OrderFlowRepository
from .order_flow_client import fetch_order_flow_rows, load_order_flow_config
from .shipment_query_config import _normalize_dps_authorization
from .daily_sync import save_authorization
from .order_flow_settings import (
    INTERVAL_SEC,
    get_order_flow_poll_settings,
    record_order_flow_poll_finished,
)

_lock = threading.Lock()


def _elapsed_sec(last_finished: str | None) -> float | None:
    text = (last_finished or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            started = datetime.strptime(text[:19], fmt)
            return (datetime.now() - started).total_seconds()
        except ValueError:
            continue
    return None


def run_order_flow_sync(
    database: Database,
    config_path: Path,
    *,
    force: bool = False,
    authorization: str | None = None,
) -> dict:
    settings = get_order_flow_poll_settings(database)
    if not force and not settings.enabled:
        return {"skipped": True, "reason": "disabled"}
    elapsed = _elapsed_sec(settings.last_finished)
    if not force and elapsed is not None and elapsed < INTERVAL_SEC:
        return {"skipped": True, "reason": "interval"}
    if not _lock.acquire(blocking=False):
        return {"skipped": True, "reason": "running"}
    try:
        saved = False
        if authorization is None:
            remote = fetch_order_flow_rows(config_path)
        else:
            # 全量拉取成功即验证成功：不额外调用其他名单，也不重复请求整份列表。
            auth = _normalize_dps_authorization(authorization) if authorization.strip() else load_order_flow_config(config_path)['authorization']
            if not auth or len(auth) > 16384 or '\n' in auth or '\r' in auth:
                raise ValueError('请输入有效的订单流转 Authorization')
            try:
                remote = fetch_order_flow_rows(config_path, authorization=auth)
            except Exception:
                raise ValueError('订单流转拉取或授权验证失败，未保存新授权，原快照已保留') from None
            if authorization.strip():
                try:
                    save_authorization(config_path, auth, 'dps_ddlz_authorization')
                    saved = True
                except Exception:
                    raise ValueError('订单流转授权保存失败，未更新本地快照') from None
        try:
            stats = OrderFlowRepository(database).apply_snapshot(remote)
            record_order_flow_poll_finished(database)
        except Exception:
            if authorization is not None:
                raise ValueError('授权已保存，但本地订单流转更新未完成，请手动刷新重试' if saved else '本地订单流转更新未完成，请手动刷新重试') from None
            raise
        print(
            f"[订单流转] {now_str()} 远端 {stats['remote']}，新增 {stats['created']}，"
            f"状态变化 {stats['changed']}，结束 {stats['ended']}",
            flush=True,
        )
        return {"skipped": False, "reason": "", **stats, **({'authorizationSaved': saved} if authorization is not None else {})}
    finally:
        _lock.release()
