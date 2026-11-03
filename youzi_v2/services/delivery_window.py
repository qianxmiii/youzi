"""Configuration-only DW prediction. Stored business dates have no inferred timezone."""

from datetime import date, datetime, timedelta


def parse_day(value) -> date | None:
    try:
        return date.fromisoformat(str(value or '').strip()[:10])
    except ValueError:
        return None


def calculate_delivery_window(shipment: dict, rules: list[dict], preference: dict | None = None,
                              *, today: date | None = None) -> dict:
    preference = preference or {}
    today = today or datetime.now().date()
    requested = preference.get('mode', 'auto')
    # DPS 0 can also mean WFS: only mapped AMZ is treated as Amazon.
    mode = ('amazon' if shipment.get('addressType') == 'AMZ' else 'range') if requested == 'auto' else requested
    result = dict(mode=mode, requestedMode=requested, start=None, end=None, copyText='',
                  source='unavailable', basis='', reason='', warnings=[],
                  manualStart=preference.get('manual_start'), manualEnd=preference.get('manual_end'),
                  updatedTime=preference.get('updated_time'))
    warnings = result['warnings']
    warnings.append('按运单记录的日期计算，未自动转换目的地时区；人工窗口请填写目的地日期。')
    if shipment.get('exceptionCode'):
        warnings.append('当前存在运输异常，自动窗口可能失准，请人工核对。')
    delivered = parse_day(shipment.get('deliveredTime'))
    if delivered or str(shipment.get('statusCode')) in ('3', 'DELIVERED'):
        result['reason'] = '运单已签收，停止自动预测；可在窗口设置中查看已确认的历史窗口。'
        # Previously confirmed window remains available, but never invent a forecast after delivery.
        if not preference.get('manual_start'):
            return result
    if str(shipment.get('statusCode')) in ('4', 'CANCELLED'):
        result['reason'] = '运单已取消，不生成窗口。'
        return result
    start = parse_day(preference.get('manual_start'))
    end = parse_day(preference.get('manual_end'))
    if start and end:
        if mode == 'amazon' and (start.weekday() != 6 or end.weekday() != 5 or (end - start).days != 6):
            result['reason'] = 'Amazon人工窗口须为同一周的周日至周六；其他日期范围请切换普通模式。'
            return result
        result.update(source='manual', basis='人工确认窗口（保持原始日期，不按周扩展）')
    else:
        eligible = [r for r in rules if r.get('enabled') and r.get('channelCode') == shipment.get('channelCode')
                    and str(r.get('startField', 'ATD')).upper() == 'ATD']
        exact = [r for r in eligible if r.get('carrierCode') and r['carrierCode'] == shipment.get('carrierCode')]
        generic = [r for r in eligible if not r.get('carrierCode')]
        matches = exact or generic
        if len(matches) != 1:
            result['reason'] = '缺少可用的渠道离港时效规则' if not matches else '时效规则不唯一，请核对配置'
            return result
        rule = matches[0]
        base = parse_day(shipment.get('atd'))
        node = '实际离港'
        if not base:
            base = parse_day(shipment.get('etd'))
            node = '预计离港'
            if base:
                warnings.append('尚无实际离港时间，当前为基于ETD的初步预计。')
        arrival = parse_day(shipment.get('ata'))
        arrival_node = '实际到港'
        if not arrival:
            arrival = parse_day(shipment.get('eta'))
            arrival_node = '预计到港'
        if not base and not arrival:
            result['reason'] = '缺少实际离港、预计离港及到港日期'
            return result
        ranges = []
        descriptions = []
        try:
            if base:
                maximum = int(rule.get('estimatedDaysMax', rule.get('estimatedDays')))
                minimum = int(rule.get('estimatedDaysMin', maximum))
                if not 1 <= minimum <= maximum:
                    raise ValueError
                ranges.append((base + timedelta(days=minimum), base + timedelta(days=maximum)))
                descriptions.append(f'{node}后{minimum}—{maximum}个自然日')
            if arrival:
                post_min = int(rule.get('postArrivalDaysMin', 7))
                post_max = int(rule.get('postArrivalDaysMax', 15))
                if not 0 <= post_min <= post_max:
                    raise ValueError
                ranges.append((arrival + timedelta(days=post_min), arrival + timedelta(days=post_max)))
                descriptions.append(f'{arrival_node}后{post_min}—{post_max}个自然日')
            # Compare each endpoint before the Amazon single-week conversion.
            start = max(item[0] for item in ranges)
            end = max(item[1] for item in ranges)
        except (KeyError, ValueError, TypeError, OverflowError):
            result['reason'] = '渠道时效天数配置无效'
            return result
        basis = '；'.join(descriptions)
        if len(ranges) > 1:
            basis += '；两种估算的起止日期分别取较晚值'
        result.update(source='configuration', basis=basis)
        if mode == 'amazon':
            # A single Sunday-Saturday week anchored to the latest predicted delivery.
            try:
                start = end - timedelta(days=(end.weekday() + 1) % 7)
                end = start + timedelta(days=6)
            except OverflowError:
                result['reason'] = '日期超出可计算范围'
                return result
            result['basis'] += '；Amazon DW取最晚预计送仓日所在周（周日—周六）'
    if end < today:
        warnings.append('窗口已过期，需重新核对；系统不会自动顺延。')
    result.update(start=start.isoformat(), end=end.isoformat(), copyText=f'{start:%m/%d} - {end:%m/%d}')
    return result
