import { api } from '@/api/client'
import type {
  Shipment,
  ShipmentImportResult,
  ShipmentListResponse,
  ShipmentPayload,
} from '@/types/shipment'
import type { TrackingLogListResponse, TrackingSyncResult } from '@/types/tracking'

export interface ListShipmentsParams {
  search?: string
  statusCode?: string
  countryCode?: string
  channelCode?: string
  minStaleDays?: number
  noTracking?: boolean
  limit?: number
  offset?: number
}

export async function listShipments(params: ListShipmentsParams): Promise<ShipmentListResponse> {
  return api<ShipmentListResponse>('/api/v1/shipments', { query: params })
}

export async function getShipmentTrackingLogs(
  shipmentId: string,
  params?: { limit?: number; offset?: number },
): Promise<TrackingLogListResponse> {
  return api<TrackingLogListResponse>(`/api/v1/shipments/${shipmentId}/tracking-logs`, {
    query: params,
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

/** 从物流 API 拉取运单轨迹并写入数据库（可能较久） */
export async function syncTracking(shipmentNos?: string[]): Promise<TrackingSyncResult> {
  const body = shipmentNos?.length ? { shipmentNos } : undefined
  return api<TrackingSyncResult>('/api/v1/shipments/sync-tracking', {
    method: 'POST',
    body,
    timeout: 600_000,
  })
}

/** @deprecated 使用 syncTracking() */
export async function syncAllTracking(): Promise<TrackingSyncResult> {
  return syncTracking()
}
