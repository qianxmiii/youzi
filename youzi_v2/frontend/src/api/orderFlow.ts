import { api } from '@/api/client'

export type OrderFlowScope = 'active' | 'mine' | 'ended' | 'all' | 'remind'

export interface OrderFlowItem {
  waybillNo: string
  customerName: string
  currentStatus: string
  previousStatus: string
  pieces: string
  weightKg: string
  chargeWeightKg: string
  volumeCbm: string
  productName: string
  warehouseName: string
  countryName: string
  channelName: string
  lastOperateTime: string
  previousOperateTime: string
  mine: boolean
  ended: boolean
  statusChanged: boolean
  statusChangedAt: string
  firstSeenTime: string
  lastSeenTime: string
  updatedTime: string
}

export interface OrderFlowSummary {
  mineCount: number
  activeCount: number
  endedCount: number
  changedCount: number
  remindCount: number
  unseenCount: number
  orderFlowPollEnabled: boolean
  orderFlowPollLastFinished: string | null
  orderFlowPollIntervalSec: number
  listSeenAt?: string
}

export interface OrderFlowList extends OrderFlowSummary {
  items: OrderFlowItem[]
  total: number
}

export interface OrderFlowNodeCount {
  status: string
  count: number
  unseen: number
}

export interface OrderFlowLog {
  status: string
  operateTime: string
  recordedTime: string
}

export function listOrderFlowStatuses() {
  return api<{ items: string[] }>('/api/v1/order-flow/statuses')
}

export function listOrderFlowCustomers() {
  return api<{ items: string[] }>('/api/v1/order-flow/customers')
}

export function listOrderFlowWarehouses() {
  return api<{ items: string[] }>('/api/v1/order-flow/warehouses')
}

export function listOrderFlowCountries() {
  return api<{ items: string[] }>('/api/v1/order-flow/countries')
}

export function listOrderFlowChannels() {
  return api<{ items: string[] }>('/api/v1/order-flow/channels')
}

export function getOrderFlowLogs(waybillNo: string) {
  return api<{ items: OrderFlowLog[] }>(`/api/v1/order-flow/${encodeURIComponent(waybillNo)}/logs`)
}

export function getOrderFlowNodes() {
  return api<{ unseenCount: number; nodes: OrderFlowNodeCount[] }>('/api/v1/order-flow/nodes')
}

export function markOrderFlowRemindersSeen() {
  return api<OrderFlowSummary>('/api/v1/order-flow/reminders/seen', { method: 'POST' })
}

export function markOrderFlowListSeen() {
  return api<{ listSeenAt: string }>('/api/v1/order-flow/list-seen', { method: 'POST' })
}

export function getOrderFlowSummary() {
  return api<OrderFlowSummary>('/api/v1/order-flow/summary')
}

export function listOrderFlow(params: {
  scope: OrderFlowScope
  search?: string
  status?: string
  customer?: string
  warehouse?: string
  country?: string
  channel?: string[]
}) {
  return api<OrderFlowList>('/api/v1/order-flow', { params })
}

export function refreshOrderFlow() {
  return api<OrderFlowSummary & { skipped: boolean; reason: string; remote?: number; created?: number; changed?: number; ended?: number }>(
    '/api/v1/order-flow/refresh',
    { method: 'POST', timeout: 120000 },
  )
}

export function getOrderFlowAuthorization() {
  return api<{configured: boolean}>('/api/v1/order-flow/authorization')
}

export function saveAndRefreshOrderFlow(authorization: string) {
  return api<{skipped: boolean; reason: string; remote?: number; created?: number; changed?: number; ended?: number; authorizationSaved?: boolean}>(
    '/api/v1/order-flow/save-and-refresh', {method:'POST',body:{authorization},retry:0,timeout:600_000},
  )
}

export function updateOrderFlowSettings(enabled: boolean) {
  return api<Pick<OrderFlowSummary, 'orderFlowPollEnabled' | 'orderFlowPollLastFinished' | 'orderFlowPollIntervalSec'>>(
    '/api/v1/order-flow/settings',
    { method: 'PUT', body: { enabled } },
  )
}

export function listPendingSalesFees() {
  return api<{ items: OrderFlowItem[]; total: number; orderFlowPollEnabled: boolean }>('/api/v1/pending-sales-fees')
}
export function refreshPendingSalesFees() {
  return api<{ skipped: boolean; reason: string; remote?: number }>('/api/v1/pending-sales-fees/refresh', { method: 'POST', timeout: 120000 })
}
