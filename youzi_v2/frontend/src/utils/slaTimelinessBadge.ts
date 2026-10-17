import { h, type VNodeChild } from 'vue'
import type { SelectRenderLabel } from 'naive-ui'
import type { SlaRiskLevel } from '@/api/shipmentSla'

/** 时效状态色标（异常跟踪列表 / 筛选） */
export type SlaTimelinessBadgeTone =
  | 'warning-soon'
  | 'overdue'
  | 'severe'
  | 'warehouse'
  | 'arrival'
  | 'dest'
  | 'delivery'
  | 'muted'

export function slaTimelinessBadgeClass(tone: SlaTimelinessBadgeTone): string {
  return `sla-timeliness-badge sla-timeliness-badge--${tone}`
}

export function toneForRiskLevel(level: SlaRiskLevel): SlaTimelinessBadgeTone {
  if (level === 'severe_overdue') return 'severe'
  if (level === 'overdue') return 'overdue'
  return 'warning-soon'
}

export function toneForAlertType(alertType: string | null | undefined): SlaTimelinessBadgeTone {
  const t = (alertType || '').trim()
  if (t === 'WAREHOUSE_NO_DEPARTURE') return 'warehouse'
  if (t === 'ARRIVAL_NO_DELIVERY') return 'arrival'
  if (t === 'DEST_WAREHOUSE_NO_DISPATCH') return 'dest'
  if (t === 'DELIVERY_TIME') return 'delivery'
  return 'muted'
}

export function toneForTimelinessFilter(value: string): SlaTimelinessBadgeTone {
  if (value === 'warning_soon') return 'warning-soon'
  if (value === 'overdue') return 'overdue'
  if (value === 'severe_overdue') return 'severe'
  if (value === 'WAREHOUSE_NO_DEPARTURE') return 'warehouse'
  if (value === 'ARRIVAL_NO_DELIVERY') return 'arrival'
  if (value === 'DEST_WAREHOUSE_NO_DISPATCH') return 'dest'
  return 'muted'
}

export function renderSlaTimelinessBadge(label: string, tone: SlaTimelinessBadgeTone) {
  return h('span', { class: slaTimelinessBadgeClass(tone) }, label)
}

export const renderTimelinessStatusSelectLabel: SelectRenderLabel = (option): VNodeChild => {
  const value = 'value' in option ? String(option.value ?? '') : ''
  const text = typeof option.label === 'string' ? option.label : ''
  if (!value) return text
  return renderSlaTimelinessBadge(text, toneForTimelinessFilter(value))
}
