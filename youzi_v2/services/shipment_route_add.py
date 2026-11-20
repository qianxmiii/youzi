"""新增 DPS 路由；不重试写请求，不直接覆盖本地最新明细状态。"""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

import requests

from .shipment_query_config import load_config_json, resolve_dps_authorization, update_logistics_config

_lock = Lock()
_inflight = set()
_APPOINTMENT_DATE_PLACEHOLDER = re.compile(r"\{预计交仓日期\}|\bN/N\b", re.ASCII)
_DELIVERED_DATE_PLACEHOLDER = '{完成派送日期}'
_WAREHOUSE_PLACEHOLDER = '{派送仓库}'


def route_options(repo):
    with repo._database.lock:
        rows = repo._database.conn.execute(
            """
            SELECT code, name_zh, dps_status
            FROM shipment_route_status_codes
            WHERE is_active = 1 OR (code = 'INFO' AND dps_status = '100')
            ORDER BY CASE WHEN code = 'INFO' AND dps_status = '100' THEN 1 ELSE 0 END, sort_order, code
            """
        ).fetchall()
    return [{'code': row['code'], 'label': row['name_zh'], 'value': str(row['dps_status']).strip()}
            for row in rows if str(row['dps_status'] or '').strip()]


def route_presets(config_path: Path) -> list[dict] | None:
    try:
        config = load_config_json(config_path)
    except (OSError, ValueError):
        return None
    block = config.get('dps_updateRoute')
    if not isinstance(block, dict) or not isinstance(block.get('presets'), list):
        return None
    presets = []
    seen = set()
    for item in block['presets']:
        if not isinstance(item, dict):
            continue
        label, status, description = (str(item.get(key) or '').strip() for key in ('label', 'status', 'text'))
        key = (status, description)
        if label and status and 0 < len(description) <= 2000 and key not in seen:
            presets.append({'label': label, 'status': status, 'text': description})
            seen.add(key)
    return presets


def save_route_presets(config_path: Path, statuses: list[dict], presets: list[dict]) -> list[dict]:
    allowed = {item['value'] for item in statuses}
    cleaned = [{key: item[key].strip() for key in ('label', 'status', 'text')} for item in presets]
    keys = {(item['status'], item['text']) for item in cleaned}
    if any(not all(item.values()) for item in cleaned):
        raise ValueError('按钮名称、明细状态和节点描述不能为空')
    if len(keys) != len(cleaned):
        raise ValueError('同一状态下的节点描述不能重复')

    def apply(config):
        block = config.get('dps_updateRoute')
        if not isinstance(block, dict):
            raise ValueError('请先配置 dps_updateRoute')
        existing = block.get('presets')
        existing = existing if isinstance(existing, list) else []
        for item in cleaned:
            if item['status'] not in allowed and not any(
                isinstance(old, dict) and all(str(old.get(key) or '').strip() == value for key, value in item.items())
                for old in existing
            ):
                raise ValueError('请选择可新增路由的明细状态')
        block['presets'] = cleaned

    update_logistics_config(config_path, apply)
    return cleaned


def _time(value, default):
    if value is None or value == '':
        return default.strftime('%Y-%m-%d %H:%M:%S')
    try:
        parsed = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        raise ValueError('时间格式须为 YYYY-MM-DD HH:mm:ss') from None
    return parsed.strftime('%Y-%m-%d %H:%M:%S')


def add_routes(repo, config_path: Path, ids, node_time, estimated_delivery_date, node_desc, status):
    ids = list(dict.fromkeys(str(i).strip() for i in ids if str(i).strip()))
    if not ids or len(ids) > 50:
        raise ValueError('请选择 1 至 50 票运单')
    description = node_desc.strip()
    if not description or len(description) > 2000:
        raise ValueError('节点描述不能为空，且最多 2000 个字符')
    if _APPOINTMENT_DATE_PLACEHOLDER.search(description):
        raise ValueError('节点描述中的预计交仓日期尚未填写')
    if _DELIVERED_DATE_PLACEHOLDER in description:
        raise ValueError('节点描述中的完成派送日期尚未填写')
    status = str(status).strip()
    if status not in {option['value'] for option in route_options(repo)}:
        raise ValueError('请选择码表中有效的 DPS 明细状态')
    now = datetime.now()
    payload = {'nodeTime': _time(node_time, now),
               'estimatedDeliveryDate': _time(estimated_delivery_date, now + timedelta(days=15)),
               'status': status}
    rows = []
    waybills = set()
    for item_id in ids:
        row = repo.get_by_id(item_id)
        if not row or not str(row.get('waybillId') or '').strip():
            raise ValueError('所选运单不存在或缺少 DPS 运单 ID，请先更新运单')
        wb = str(row['waybillId']).strip()
        if wb in waybills:
            raise ValueError('所选运单包含重复的 DPS 运单 ID，请先核对')
        row_description = description
        if _WAREHOUSE_PLACEHOLDER in description:
            warehouse = str(row.get('addressCode') or '').strip()
            if not warehouse:
                raise ValueError('部分运单缺少派送仓库，请补齐后再新增路由')
            row_description = description.replace(_WAREHOUSE_PLACEHOLDER, warehouse)
            if len(row_description) > 2000:
                raise ValueError('替换派送仓库后的节点描述最多 2000 个字符')
        waybills.add(wb)
        rows.append((row, row_description))
    config = load_config_json(config_path)
    block = config.get('dps_updateRoute') or {}
    if not isinstance(block, dict) or not str(block.get('url') or '').strip():
        raise ValueError('请配置 dps_updateRoute.url')
    auth = resolve_dps_authorization(config, block)
    method = str(block.get('method') or 'POST').upper()
    if not auth or method not in {'POST', 'PUT'}:
        raise ValueError('请检查 DPS 鉴权及 dps_updateRoute.method（POST/PUT）')
    try:
        timeout = min(60, max(1, int(block.get('timeout') or 30)))
    except (ValueError, TypeError):
        raise ValueError('dps_updateRoute.timeout 须为秒数') from None
    with _lock:
        if waybills & _inflight:
            raise ValueError('所选运单正在新增路由，请等待原请求结束并核对结果')
        _inflight.update(waybills)

    def submit(entry):
        row, row_description = entry
        result = {'id': row['id'], 'shipmentNo': row['shipmentNo']}
        try:
            response = requests.request(method, block['url'], json={**payload, 'nodeDesc': row_description, 'commerceWaybillId': str(row['waybillId']).strip()},
                                        headers={'Authorization': auth, 'Content-Type': 'application/json'}, timeout=timeout)
            if response.status_code in (401, 403):
                return {**result, 'status': 'failed', 'message': 'DPS 鉴权失效，请更新授权'}
            if not 200 <= response.status_code < 300:
                return {**result, 'status': 'unknown', 'message': f'HTTP {response.status_code}，请核对远端结果后再操作'}
            body = response.json()
            if not isinstance(body, dict) or 'code' not in body:
                return {**result, 'status': 'unknown', 'message': 'DPS 未明确确认成功，请核对远端结果'}
            if body['code'] not in (0, '0', 200, '200'):
                return {**result, 'status': 'failed', 'message': 'DPS 返回业务失败，请核对节点与授权'}
            return {**result, 'status': 'success', 'message': '新增成功'}
        except (requests.RequestException, ValueError):
            return {**result, 'status': 'unknown', 'message': '请求异常或响应无法确认，请核对远端结果，勿直接重复新增'}

    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(submit, rows))
    finally:
        with _lock:
            _inflight.difference_update(waybills)
    return {'items': results, 'total': len(results),
            'succeeded': sum(r['status'] == 'success' for r in results),
            'failed': sum(r['status'] == 'failed' for r in results),
            'unknown': sum(r['status'] == 'unknown' for r in results)}
