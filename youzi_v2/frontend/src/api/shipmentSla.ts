import { api } from './client'

export type SlaRiskLevel = 'warning_soon' | 'overdue' | 'severe_overdue'
export type SlaAlertStatus = 'open' | 'acknowledged' | 'converted' | 'resolved' | 'ignored'

export interface ChannelSlaRule {
  id: string
  channelCode: string
  carrierCode: string
  startField: string
  estimatedDays: number
  warningDays: number
  severeOverdueDays: number
  enabled: boolean
  note: string
  createdTime: string
  updatedTime: string
}

export interface ChannelSlaRulePayload {
  estimatedDays: number
  carrierCode?: string
  startField?: string
  warningDays?: number
  severeOverdueDays?: number
  enabled?: boolean
  note?: string
}

export interface ShipmentSlaAlert {
  id: string
  shipmentId: string
  shipmentNo: string
  alertType: string
  riskLevel: SlaRiskLevel
  status: SlaAlertStatus
  severity: string
  ruleId: string
  ruleScope: string
  channelCode: string
  carrierCode: string
  startField: string
  startTime: string
  dueDate: string
  warningDate: string
  convertedExceptionCode: string
  convertedEventId: string
  acknowledgedTime: string | null
  resolvedTime: string | null
  ignoredTime: string | null
  followUpCount: number
  lastFollowUpTime: string | null
  lastFollowUpDaysAgo: number | null
  owner: string
  note: string
  eventKey: string
  createdTime: string
  updatedTime: string
  daysUntilDue: number | null
  overdueDays: number
  daysInTransit: number | null
  estimatedDays: number | null
  customer?: string | null
  destinationPort?: string | null
  atd?: string | null
  warehouseEntryTime?: string | null
  expectedDeliveryTime?: string | null
  deliveredTime?: string | null
  exceptionCode?: string | null
  exceptionNameZh?: string | null
  exceptionDurationSeconds?: number | null
  exceptionDurationLabel?: string | null
  latestTrackingDesc?: string | null
  latestTrackingTime?: string | null
  channelNameZh?: string | null
  carrierNameZh?: string | null
}

export interface ShipmentSlaAlertListResponse {
  items: ShipmentSlaAlert[]
  total: number
  limit: number
  offset: number
}

export interface ShipmentSlaSummary {
  pendingOpen: number
  severeOverdue: number
  overdue: number
  warningSoon: number
  currentExceptions: number
}

export async function listChannelSlaRules(channelCode: string): Promise<{ items: ChannelSlaRule[] }> {
  return api(`/api/v1/channels/${encodeURIComponent(channelCode)}/sla-rules`)
}

export async function upsertChannelSlaRule(
  channelCode: string,
  payload: ChannelSlaRulePayload,
): Promise<ChannelSlaRule> {
  return api(`/api/v1/channels/${encodeURIComponent(channelCode)}/sla-rules`, {
    method: 'PUT',
    body: payload,
  })
}

export async function deleteChannelSlaRule(channelCode: string, ruleId: string): Promise<void> {
  await api(
    `/api/v1/channels/${encodeURIComponent(channelCode)}/sla-rules/${encodeURIComponent(ruleId)}`,
    { method: 'DELETE' },
  )
}

export async function listShipmentSlaAlerts(params: {
  scope?: 'todo' | 'all'
  riskLevel?: string
  alertType?: string
  status?: string
  hasException?: boolean
  exceptionCode?: string
  channelCode?: string
  carrierCode?: string
  customer?: string
  search?: string
  limit?: number
  offset?: number
}): Promise<ShipmentSlaAlertListResponse> {
  const query: Record<string, string> = {}
  if (params.scope) query.scope = params.scope
  if (params.riskLevel) query.riskLevel = params.riskLevel
  if (params.alertType) query.alertType = params.alertType
  if (params.status) query.status = params.status
  if (params.hasException != null) query.hasException = String(params.hasException)
  if (params.exceptionCode) query.exceptionCode = params.exceptionCode
  if (params.channelCode) query.channelCode = params.channelCode
  if (params.carrierCode) query.carrierCode = params.carrierCode
  if (params.customer) query.customer = params.customer
  if (params.search) query.search = params.search
  if (params.limit != null) query.limit = String(params.limit)
  if (params.offset != null) query.offset = String(params.offset)
  return api('/api/v1/shipment-sla-alerts', { query })
}

export async function getShipmentSlaSummary(): Promise<ShipmentSlaSummary> {
  return api('/api/v1/shipment-sla-alerts/summary')
}

export async function getShipmentSlaTodoNotifications(limit = 20): Promise<{
  items: ShipmentSlaAlert[]
  pendingCount: number
}> {
  return api('/api/v1/shipment-sla-alerts/todo-notifications', {
    query: { limit: String(limit) },
  })
}

export async function evaluateShipmentSlaAlerts(): Promise<{
  skipped: boolean
  reason?: string
  scanned: number
  created: number
  updated: number
  resolved: number
}> {
  return api('/api/v1/shipment-sla-alerts/evaluate', { method: 'POST' })
}

export async function followUpShipmentSlaAlert(alertId: string): Promise<void> {
  await api(`/api/v1/shipment-sla-alerts/${encodeURIComponent(alertId)}/follow-up`, {
    method: 'POST',
  })
}

/** @deprecated 使用 followUpShipmentSlaAlert */
export async function acknowledgeShipmentSlaAlert(alertId: string): Promise<void> {
  return followUpShipmentSlaAlert(alertId)
}

export async function resolveShipmentSlaAlert(alertId: string): Promise<void> {
  await api(`/api/v1/shipment-sla-alerts/${encodeURIComponent(alertId)}/resolve`, {
    method: 'POST',
  })
}

export async function ignoreShipmentSlaAlert(alertId: string): Promise<void> {
  await api(`/api/v1/shipment-sla-alerts/${encodeURIComponent(alertId)}/ignore`, {
    method: 'POST',
  })
}

export async function convertShipmentSlaAlert(
  alertId: string,
  payload: { exceptionCode?: string; note?: string },
): Promise<{ ok: boolean; eventId: string }> {
  return api(`/api/v1/shipment-sla-alerts/${encodeURIComponent(alertId)}/convert`, {
    method: 'POST',
    body: payload,
  })
}

export async function updateShipmentSlaAlertNote(alertId: string, note: string): Promise<void> {
  await api(`/api/v1/shipment-sla-alerts/${encodeURIComponent(alertId)}/note`, {
    method: 'PATCH',
    body: { note },
  })
}

function slaAlertTitle(riskLevel: SlaRiskLevel): string {
  if (riskLevel === 'severe_overdue') return '运输时效严重超时'
  if (riskLevel === 'overdue') return '运输时效已超时'
  return '运输时效即将超时'
}

function slaAlertMessage(alert: ShipmentSlaAlert): string {
  const days = alert.daysUntilDue
  if (days != null && days >= 0) {
    return `运单 ${alert.shipmentNo} · 预估截止 ${alert.dueDate}，剩余 ${days} 天。`
  }
  const overdue = alert.overdueDays || 0
  return `运单 ${alert.shipmentNo} · 预估截止 ${alert.dueDate}，已超期 ${overdue} 天。`
}

export function slaAlertAsCard(alert: ShipmentSlaAlert) {
  return {
    title: slaAlertTitle(alert.riskLevel),
    message: slaAlertMessage(alert),
    subtitle: alert.shipmentNo,
    customerName: alert.customer || '',
    ruleType: 'SLA_TRANSIT',
    severity: alert.severity,
    triggeredAt: alert.updatedTime || alert.createdTime,
  }
}
