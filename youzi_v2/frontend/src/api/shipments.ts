import { api } from '@/api/client'
import type {
  Shipment,
  ShipmentImportResult,
  ShipmentListResponse,
  ShipmentPayload,
} from '@/types/shipment'
import type {
  TrackingLogListResponse,
  TrackingSyncDailyStats,
  TrackingSyncResult,
} from '@/types/tracking'

export interface ShipmentFilterOptions {
  customers: string[]
  carrierCodes: string[]
  countryCodes: string[]
  channelCodes: string[]
  statusCodes: string[]
}

/** 仅发送有值的查询参数，避免 ofetch 序列化异常 */
export function buildShipmentListQuery(params: ListShipmentsParams): Record<string, string | string[]> {
  const q: Record<string, string | string[]> = {}
  if (params.search?.trim()) q.search = params.search.trim()
  if (params.shipmentNos?.length) q.shipmentNos = params.shipmentNos
  if (params.statusCode?.trim()) q.statusCode = params.statusCode.trim()
  if (params.customer?.trim()) q.customer = params.customer.trim()
  if (params.carrierCode?.trim()) q.carrierCode = params.carrierCode.trim()
  if (params.countryCode?.trim()) q.countryCode = params.countryCode.trim()
  if (params.channelCode?.trim()) q.channelCode = params.channelCode.trim()
  if (params.minStaleDays != null && params.minStaleDays > 0) {
    q.minStaleDays = String(params.minStaleDays)
  }
  if (params.noTracking) q.noTracking = 'true'
  if (params.limit != null) q.limit = String(params.limit)
  if (params.offset != null) q.offset = String(params.offset)
  return q
}

export interface ListShipmentsParams {
  search?: string
  /** 批量精确查询运单号 / 客户订单号（与 search 二选一） */
  shipmentNos?: string[]
  statusCode?: string
  customer?: string
  carrierCode?: string
  countryCode?: string
  channelCode?: string
  minStaleDays?: number
  noTracking?: boolean
  limit?: number
  offset?: number
}

export async function listShipments(params: ListShipmentsParams): Promise<ShipmentListResponse> {
  return api<ShipmentListResponse>('/api/v1/shipments', { query: buildShipmentListQuery(params) })
}

export async function getShipmentFilterOptions(): Promise<ShipmentFilterOptions> {
  return api<ShipmentFilterOptions>('/api/v1/shipments/filter-options')
}

export async function getShipmentTrackingLogs(
  shipmentId: string,
  params?: { limit?: number; offset?: number },
): Promise<TrackingLogListResponse> {
  return api<TrackingLogListResponse>(`/api/v1/shipments/${shipmentId}/tracking-logs`, {
    query: params,
  })
}

export async function getShipmentCarrierTrackingLogs(
  shipmentId: string,
  params?: { limit?: number; offset?: number },
): Promise<TrackingLogListResponse> {
  return api<TrackingLogListResponse>(`/api/v1/shipments/${shipmentId}/carrier-tracking-logs`, {
    query: params,
  })
}

export async function getTrackingSyncDailyStats(
  source: 'internal' | 'carrier',
): Promise<TrackingSyncDailyStats> {
  return api<TrackingSyncDailyStats>('/api/v1/shipments/tracking-sync/daily-stats', {
    query: { source },
  })
}

export async function getShipment(id: string): Promise<Shipment> {
  return api<Shipment>(`/api/v1/shipments/${id}`)
}

export async function createShipment(payload: ShipmentPayload): Promise<Shipment> {
  return api<Shipment>('/api/v1/shipments', { method: 'POST', body: payload })
}

export async function updateShipment(
  id: string,
  payload: Partial<ShipmentPayload>,
): Promise<Shipment> {
  const { shipmentNo: _sn, ...body } = payload
  return api<Shipment>(`/api/v1/shipments/${id}`, { method: 'PUT', body })
}

export async function deleteShipment(id: string): Promise<void> {
  await api(`/api/v1/shipments/${id}`, { method: 'DELETE' })
}

export async function importShipmentsExcel(file: File): Promise<ShipmentImportResult> {
  const form = new FormData()
  form.append('file', file)
  return api<ShipmentImportResult>('/api/v1/shipments/import', {
    method: 'POST',
    body: form,
  })
}

/** 同步内部路由轨迹 */
export async function syncTracking(shipmentNos?: string[]): Promise<TrackingSyncResult> {
  const body = shipmentNos?.length ? { shipmentNos } : undefined
  return api<TrackingSyncResult>('/api/v1/shipments/sync-tracking', {
    method: 'POST',
    body,
    timeout: 600_000,
  })
}

/** 同步承运商轨迹（全库在途或指定单号） */
export async function syncCarrierTracking(shipmentNos?: string[]): Promise<TrackingSyncResult> {
  const body = shipmentNos?.length ? { shipmentNos } : undefined
  return api<TrackingSyncResult>('/api/v1/shipments/sync-carrier-tracking', {
    method: 'POST',
    body,
    timeout: 600_000,
  })
}

/** @deprecated 使用 syncTracking() */
export async function syncAllTracking(): Promise<TrackingSyncResult> {
  return syncTracking()
}
