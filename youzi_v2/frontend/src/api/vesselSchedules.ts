import { api } from '@/api/client'
import type {
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
