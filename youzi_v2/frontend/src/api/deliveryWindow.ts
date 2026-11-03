import { api } from './client'

export type WindowMode = 'auto' | 'range' | 'amazon'
export interface WindowSettings {
  mode: WindowMode
  manualStart: string | null
  manualEnd: string | null
}
export interface DeliveryWindow {
  mode: WindowMode
  requestedMode: WindowMode
  start: string | null
  end: string | null
  copyText: string
  source: 'configuration' | 'manual' | 'unavailable'
  basis: string
  reason: string
  warnings: string[]
  manualStart: string | null
  manualEnd: string | null
  updatedTime: string | null
}
const path = (id: string) => `/api/v1/shipments/${encodeURIComponent(id)}/delivery-window`
export const getDeliveryWindow = (id: string) => api<DeliveryWindow>(path(id))
export const previewDeliveryWindow = (id: string, body: WindowSettings) =>
  api<DeliveryWindow>(`${path(id)}/preview`, { method: 'POST', body })
export const saveDeliveryWindow = (id: string, body: WindowSettings) =>
  api<DeliveryWindow>(path(id), { method: 'PUT', body })

export interface HistoryMetric {
  ticketCount: number
  batchCount: number
  p50Days: number | null
  p90Days: number | null
}
export interface DeliveryHistory {
  scope: string
  lookbackDays: number
  minBatchCount: number
  completedCount: number
  independentBatchCount: number
  unknownBatchTickets: number
  longExceptionCount: number
  inTransitCount: number
  metrics: Record<'full' | 'postArrival', { actual: HistoryMetric; normal: HistoryMetric; recent30: HistoryMetric }>
  prediction: { start: string; end: string; copyText: string; basis: string; warnings: string[] } | null
  reason: string
  warnings: string[]
  truncated: boolean
}
export const getDeliveryWindowHistory = (id: string, mode: WindowMode) =>
  api<DeliveryHistory>(`${path(id)}/history`, { query: { mode } })
