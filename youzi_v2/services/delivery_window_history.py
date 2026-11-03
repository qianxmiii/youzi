"""Read-only cohort reference; delivery is arrival at the destination warehouse."""

import math
from collections import defaultdict
from datetime import date, timedelta
from statistics import median

from .delivery_window import calculate_delivery_window, parse_day
from ..db.shipment_performance_statistics_repository import _percentile

LOOKBACK_DAYS = 90
MIN_BATCHES = 5
MAX_ROWS = 10_000


def _batch(row: dict) -> tuple | None:
    departure = parse_day(row.get('atd'))
    if not departure:
        return None
    voyage = str(row.get('vessel_voyage') or '').strip().upper()
    container = str(row.get('container_no') or '').strip().upper()
    destination = str(row.get('destination_port_code') or '').strip().upper()
    if voyage:
        return ('voyage', voyage, destination, departure)
    if container:
        return ('container', container, departure)
    return None


def _metric(rows: list[dict], field: str, today: date, *, normal=False, recent=False) -> dict:
    groups = defaultdict(list)
    ticket_count = 0
    for row in rows:
        if normal and (row.get('long_exception') or row.get('exception_code')):
            continue
        finish, start = parse_day(row.get('delivered_time')), parse_day(row.get(field))
        if not finish or not start or finish < start or start > today:
            continue
        departure, arrival = parse_day(row.get('atd')), parse_day(row.get('ata'))
        if (departure and arrival and arrival < departure) or (departure and finish < departure) or (arrival and finish < arrival):
            continue
        if recent and finish < today - timedelta(days=29):
            continue
        ticket_count += 1
        key = _batch(row)
        if key:
            groups[key].append((finish - start).days)
    # One median per known batch: a large sailing does not dominate the percentile.
    values = [float(median(items)) for items in groups.values()]
    return dict(ticketCount=ticket_count, batchCount=len(values),
                p50Days=_percentile(values, 50), p90Days=_percentile(values, 90))


def summarize_history(shipment: dict, rows: list[dict], *, mode='auto', today: date | None = None,
                      in_transit_count=0, truncated=False) -> dict:
    today = today or date.today()
    cutoff = today - timedelta(days=LOOKBACK_DAYS - 1)
    # Keep country and address type fixed when known; never relax across these boundaries.
    fields = [('country_code', 'countryCode'), ('address_type', 'addressType')]
    valid = [r for r in rows if r.get('id') != shipment.get('id')
             and str(r.get('status_code') or '') not in ('4', 'CANCELLED')
             and parse_day(r.get('delivered_time'))
             and cutoff <= parse_day(r['delivered_time']) <= today
             and r.get('channel_code') == shipment.get('channelCode')
             and all(not shipment.get(api) or r.get(db) == shipment[api] for db, api in fields)]
    warnings = ['仅统计近90天已送达目的仓的运单；未完成慢单不在分位数中，在途数量仅作偏差提示，不代表已校正。',
                '船名航次/柜号与离港日期用于识别批次，属于近似分组；缺少批次信息的票不进入批次分位数。',
                'P50—P90是历史批次分布参考，不代表未来窗口的命中率。']
    if not shipment.get('countryCode') or not shipment.get('addressType'):
        warnings.append('当前运单国家或地址类型不完整，相应维度未限制，参考可比性较低。')
    filters = []
    if shipment.get('carrierCode'):
        filters.append(('carrier_code', shipment['carrierCode']))
    if shipment.get('destinationPortCode'):
        filters.append(('destination_port_code', shipment['destinationPortCode']))
    levels = [filters]
    # Relax carrier first, then port; always make the actual scope explicit.
    if any(key == 'carrier_code' for key, _ in filters):
        levels.append([(key, value) for key, value in filters if key != 'carrier_code'])
    levels.append([])
    sample = []
    selected = []
    for level in levels:
        selected = level
        sample = [r for r in valid if all(r.get(key) == value for key, value in level)]
        if len({_batch(r) for r in sample} - {None}) >= MIN_BATCHES:
            break
    scope = ['同渠道']
    if shipment.get('countryCode'):
        scope.append('同国家')
    if shipment.get('addressType'):
        scope.append('同地址类型')
    scope += ['同承运商' if key == 'carrier_code' else '同目的港' for key, _ in selected]
    if selected != filters:
        warnings.append('细分批次不足，已放宽承运商或目的港条件；请核对实际匹配范围。')
    metrics = {}
    for key, field in [('full', 'atd'), ('postArrival', 'ata')]:
        metrics[key] = dict(actual=_metric(sample, field, today),
                            normal=_metric(sample, field, today, normal=True),
                            recent30=_metric(sample, field, today, recent=True))
    history = dict(lookbackDays=LOOKBACK_DAYS, minBatchCount=MIN_BATCHES,
                   scope=' / '.join(scope), completedCount=len(sample),
                   independentBatchCount=len({_batch(r) for r in sample} - {None}),
                   unknownBatchTickets=sum(_batch(r) is None for r in sample),
                   longExceptionCount=sum(bool(r.get('long_exception')) for r in sample),
                   inTransitCount=in_transit_count, metrics=metrics, warnings=warnings,
                   prediction=None, reason='', truncated=truncated)
    required = []
    if parse_day(shipment.get('atd')) or parse_day(shipment.get('etd')):
        required.append('full')
    if parse_day(shipment.get('ata')) or parse_day(shipment.get('eta')):
        required.append('postArrival')
    if truncated:
        history['reason'] = '匹配数据超过读取上限，暂不生成历史窗口，请先缩小统计范围。'
    elif not required:
        history['reason'] = '缺少可用的离港或到港日期，不能生成历史窗口。'
    elif any(metrics[key]['actual']['batchCount'] < MIN_BATCHES for key in required):
        history['reason'] = '所需时效段不足5个可识别批次，继续使用配置窗口。'
    else:
        # Actual performance includes delayed/abnormal shipments, not only the normal subset.
        rule = dict(channelCode=shipment.get('channelCode'), enabled=True, startField='ATD',
                    carrierCode='', estimatedDays=1)
        for key, low, high in [('full', 'estimatedDaysMin', 'estimatedDaysMax'),
                               ('postArrival', 'postArrivalDaysMin', 'postArrivalDaysMax')]:
            metric = metrics[key]['actual']
            if key in required:
                rule[low] = max(1 if key == 'full' else 0, math.ceil(metric['p50Days']))
                rule[high] = max(rule[low], math.ceil(metric['p90Days']))
        prediction = calculate_delivery_window(shipment, [rule], dict(mode=mode), today=today)
        if prediction['copyText']:
            history['prediction'] = dict(start=prediction['start'], end=prediction['end'],
                                          copyText=prediction['copyText'], warnings=prediction['warnings'],
                                          basis='含异常实际履约批次P50—P90；' + prediction['basis'])
        else:
            history['reason'] = prediction['reason']
    return history


def load_delivery_history(conn, shipment: dict, *, mode='auto', today: date | None = None) -> dict:
    today = today or date.today()
    cutoff = (today - timedelta(days=LOOKBACK_DAYS - 1)).isoformat()
    conditions = ['s.channel_code = ?', 's.id != ?']
    params = [shipment.get('channelCode') or '', shipment.get('id') or '']
    for column, api in [('country_code', 'countryCode'), ('address_type', 'addressType')]:
        if shipment.get(api):
            conditions.append(f's.{column} = ?')
            params.append(shipment[api])
    where = ' AND '.join(conditions)
    rows = conn.execute(f"""
        SELECT s.id, s.channel_code, s.country_code, s.address_type, s.carrier_code,
               s.destination_port_code, s.vessel_voyage, s.container_no,
               s.atd, s.ata, s.delivered_time, s.status_code, s.exception_code,
               EXISTS (SELECT 1 FROM shipment_exception_events e
                   WHERE e.shipment_no = s.shipment_no
                     AND julianday(COALESCE(NULLIF(TRIM(e.closed_time), ''), ?))
                         - julianday(e.opened_time) > 7) AS long_exception
        FROM shipments s WHERE {where}
          AND substr(s.delivered_time, 1, 10) BETWEEN ? AND ?
        ORDER BY s.delivered_time DESC, s.id LIMIT ?
    """, [today.isoformat(), *params, cutoff, today.isoformat(), MAX_ROWS + 1]).fetchall()
    pending = conn.execute(f"""
        SELECT COUNT(*) FROM shipments s WHERE {where}
          AND substr(s.atd, 1, 10) BETWEEN ? AND ?
          AND NULLIF(TRIM(s.delivered_time), '') IS NULL
          AND COALESCE(s.status_code, '') NOT IN ('4', 'CANCELLED', '3', 'DELIVERED')
    """, [*params, cutoff, today.isoformat()]).fetchone()[0]
    return summarize_history(shipment, [dict(r) for r in rows[:MAX_ROWS]], mode=mode,
                             today=today, in_transit_count=pending, truncated=len(rows) > MAX_ROWS)
