import { api } from '@/api/client'
import type {
  CarrierVesselSearchResponse,
  ExternalSchedulePreview,
  ExternalScheduleSyncResult,
  MaritimeScheduleProvidersResponse,
  VesselScheduleSyncAllResult,
  VesselVoyageDetail,
  VesselVoyageListResponse,
  VesselVoyagePayload,
  VoyageImportResult,
  VoyageShipmentListResponse,
  MaritimeStatus,
} from '@/types/vesselSchedule'

export async function listVesselSchedules(params?: {
  search?: string
  limit?: number
  offset?: number
}): Promise<VesselVoyageListResponse> {
  const q: Record<string, string | number> = {}
  if (params?.search) q.search = params.search
  if (params?.limit != null) q.limit = params.limit
  if (params?.offset != null) q.offset = params.offset
  return api<VesselVoyageListResponse>('/api/v1/vessel-schedules', { query: q })
}

export async function getVesselSchedule(voyageId: string): Promise<VesselVoyageDetail> {
  return api<VesselVoyageDetail>(`/api/v1/vessel-schedules/${encodeURIComponent(voyageId)}`)
}

export async function createVesselSchedule(payload: VesselVoyagePayload): Promise<VesselVoyageDetail> {
  return api<VesselVoyageDetail>('/api/v1/vessel-schedules', { method: 'POST', body: payload })
}

export async function updateVesselSchedule(
  voyageId: string,
  payload: Partial<VesselVoyagePayload>,
): Promise<VesselVoyageDetail> {
  return api<VesselVoyageDetail>(`/api/v1/vessel-schedules/${encodeURIComponent(voyageId)}`, {
    method: 'PATCH',
    body: payload,
  })
}

export async function deleteVesselSchedule(voyageId: string): Promise<void> {
  await api(`/api/v1/vessel-schedules/${encodeURIComponent(voyageId)}`, { method: 'DELETE' })
}

export async function listVoyageShipments(
  voyageId: string,
  params?: {
    maritimeStatus?: MaritimeStatus
    limit?: number
    offset?: number
  },
): Promise<VoyageShipmentListResponse> {
  const q: Record<string, string | number> = {}
  if (params?.maritimeStatus) q.maritimeStatus = params.maritimeStatus
  if (params?.limit != null) q.limit = params.limit
  if (params?.offset != null) q.offset = params.offset
  return api<VoyageShipmentListResponse>(
    `/api/v1/vessel-schedules/${encodeURIComponent(voyageId)}/shipments`,
    { query: q },
  )
}

export async function importVesselScheduleExcel(file: File): Promise<VoyageImportResult> {
  const form = new FormData()
  form.append('file', file)
  return api<VoyageImportResult>('/api/v1/vessel-schedules/import', { method: 'POST', body: form })
}

export function vesselScheduleTemplateUrl(): string {
  const base = import.meta.env.VITE_API_BASE || ''
  return `${base}/api/v1/vessel-schedules/template`
}

export async function listMaritimeScheduleProviders(): Promise<MaritimeScheduleProvidersResponse> {
  return api<MaritimeScheduleProvidersResponse>('/api/v1/vessel-schedules/providers')
}

export async function searchCarrierVessels(
  shippingCompany: string,
  prefix: string,
  signal?: AbortSignal,
): Promise<CarrierVesselSearchResponse> {
  return api<CarrierVesselSearchResponse>('/api/v1/vessel-schedules/vessels/search', {
    query: {
      shippingCompany: shippingCompany.trim(),
      prefix: prefix.trim(),
    },
    signal,
  })
}

export async function previewExternalVesselSchedule(
  shippingCompany: string,
  vesselCode: string,
  period = 28,
): Promise<ExternalSchedulePreview> {
  return api<ExternalSchedulePreview>('/api/v1/vessel-schedules/fetch/preview', {
    query: {
      shippingCompany: shippingCompany.trim(),
      vesselCode: vesselCode.trim().toUpperCase(),
      period,
    },
  })
}

export async function syncExternalVesselSchedule(
  shippingCompany: string,
  vesselCode: string,
  period = 28,
): Promise<ExternalScheduleSyncResult> {
  return api<ExternalScheduleSyncResult>('/api/v1/vessel-schedules/fetch/sync', {
    method: 'POST',
    body: {
      shippingCompany: shippingCompany.trim(),
      vesselCode: vesselCode.trim().toUpperCase(),
      period,
    },
  })
}

export async function syncAllExternalVesselSchedules(
  period = 28,
): Promise<VesselScheduleSyncAllResult> {
  return api<VesselScheduleSyncAllResult>('/api/v1/vessel-schedules/fetch/sync-all', {
    method: 'POST',
    body: { period },
  })
}

export async function subscribePortCall(portCallId: string): Promise<{ subscribed: boolean }> {
  return api(`/api/v1/vessel-schedules/port-calls/${encodeURIComponent(portCallId)}/subscribe`, {
    method: 'POST',
  })
}

export async function unsubscribePortCall(portCallId: string): Promise<{ subscribed: boolean }> {
  return api(`/api/v1/vessel-schedules/port-calls/${encodeURIComponent(portCallId)}/subscribe`, {
    method: 'DELETE',
  })
}
