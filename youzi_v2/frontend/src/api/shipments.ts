import { api } from '@/api/client'
import type {
  Shipment,
  ShipmentBatchResult,
  ShipmentExceptionBatchResult,
  ShipmentExceptionEvent,
  ShipmentImportResult,
  ShipmentListResponse,
  ShipmentDpsSyncByOrderResult,
  ShipmentPayload,
} from '@/types/shipment'
import type {
  TrackingTimeCandidate,
  TrackingTimeRecalculateResult,
} from '@/types/trackingTimeWriteback'
import type {
  TrackingLogListResponse,
  TrackingSyncDailyStats,
  TrackingSyncResult,
} from '@/types/tracking'
import type {
  TrackingFreshnessBucket,
  TrackingFreshnessStats,
} from '@/utils/trackingFreshness'

import type { ShipmentGroupFilterOption } from '@/types/shipmentGroup'

export interface ShipmentCarrierFilterOption {
  code: string
  nameZh: string
}

export interface ShipmentFilterOptions {
  customers: string[]
  carriers: ShipmentCarrierFilterOption[]
  carrierCodes: string[]
  countryCodes: string[]
  channelCodes: string[]
  channelNameZhs: string[]
  channelCategories: string[]
  statusCodes: string[]
  exceptionCodes: string[]
  exceptionTypes: { code: string; nameZh: string }[]
  groups: ShipmentGroupFilterOption[]
}

/** 仅发送有值的查询参数，避免 ofetch 序列化异常 */
export function buildShipmentListQuery(params: ListShipmentsParams): Record<string, string | string[]> {
  const q: Record<string, string | string[]> = {}
  if (params.search?.trim()) q.search = params.search.trim()
  if (params.trackingSearch?.trim()) q.trackingSearch = params.trackingSearch.trim()
  if (params.shipmentNos?.length) q.shipmentNos = params.shipmentNos
  if (params.statusCode?.trim()) q.statusCode = params.statusCode.trim()
  if (params.exceptionCode?.trim()) q.exceptionCode = params.exceptionCode.trim()
  if (params.hasException === true) q.hasException = 'true'
  if (params.hasException === false) q.hasException = 'false'
  if (params.customer?.trim()) q.customer = params.customer.trim()
  if (params.vipOnly === true) q.vipOnly = 'true'
  if (params.vipOnly === false) q.vipOnly = 'false'
  if (params.carrierCode?.trim()) q.carrierCode = params.carrierCode.trim()
  if (params.countryCode?.trim()) q.countryCode = params.countryCode.trim()
  if (params.channelCode?.trim()) q.channelCode = params.channelCode.trim()
  if (params.channelNameZh?.trim()) q.channelNameZh = params.channelNameZh.trim()
  if (params.channelCategory?.trim()) q.channelCategory = params.channelCategory.trim()
  if (params.vesselVoyage?.trim()) q.vesselVoyage = params.vesselVoyage.trim()
  if (params.customerNo?.trim()) q.customerNo = params.customerNo.trim()
  if (params.destinationPortCode?.trim()) q.destinationPortCode = params.destinationPortCode.trim()
  if (params.addressKeyword?.trim()) q.addressKeyword = params.addressKeyword.trim()
  if (params.timeField?.trim()) q.timeField = params.timeField.trim()
  if (params.timeFrom?.trim()) q.timeFrom = params.timeFrom.trim()
  if (params.timeTo?.trim()) q.timeTo = params.timeTo.trim()
  const dateKeys = [
    ['etdFrom', 'etdTo'],
    ['atdFrom', 'atdTo'],
    ['etaFrom', 'etaTo'],
    ['ataFrom', 'ataTo'],
    ['expectedDeliveryFrom', 'expectedDeliveryTo'],
    ['deliveredFrom', 'deliveredTo'],
    ['createdFrom', 'createdTo'],
    ['updatedFrom', 'updatedTo'],
  ] as const
  for (const [fromKey, toKey] of dateKeys) {
    const from = params[fromKey]?.trim()
    const to = params[toKey]?.trim()
    if (from) q[fromKey] = from
    if (to) q[toKey] = to
  }
  if (params.missingEtd) q.missingEtd = 'true'
  if (params.missingAtd) q.missingAtd = 'true'
  if (params.missingEta) q.missingEta = 'true'
  if (params.missingAta) q.missingAta = 'true'
  if (params.missingExpectedDelivery) q.missingExpectedDelivery = 'true'
  if (params.missingDelivered) q.missingDelivered = 'true'
  if (params.notDelivered) q.notDelivered = 'true'
  if (params.hasAta) q.hasAta = 'true'
  if (params.deliveryRisk?.trim()) q.deliveryRisk = params.deliveryRisk.trim()
  if (params.internalFreshness) q.internalFreshness = params.internalFreshness
  if (params.carrierFreshness) q.carrierFreshness = params.carrierFreshness
  if (params.carrierAheadOfInternal) q.carrierAheadOfInternal = 'true'
  if (params.pendingTrackingTimeReview) q.pendingTrackingTimeReview = 'true'
  if (params.minStaleDays != null && params.minStaleDays > 0) {
    q.minStaleDays = String(params.minStaleDays)
  }
  if (params.noTracking) q.noTracking = 'true'
  if (params.noZipcode) q.noZipcode = 'true'
  if (params.groupId?.trim()) q.groupId = params.groupId.trim()
  if (params.groupNo?.trim()) q.groupNo = params.groupNo.trim()
  if (params.ruleType?.trim()) q.ruleType = params.ruleType.trim()
  if (params.hasRule === true) q.hasRule = 'true'
  if (params.hasRule === false) q.hasRule = 'false'
  if (params.hasGroup === true) q.hasGroup = 'true'
  if (params.hasGroup === false) q.hasGroup = 'false'
  if (params.sortBy?.trim()) q.sortBy = params.sortBy.trim()
  if (params.sortOrder === 'asc' || params.sortOrder === 'desc') {
    q.sortOrder = params.sortOrder
  }
  if (params.limit != null) q.limit = String(params.limit)
  if (params.offset != null) q.offset = String(params.offset)
  return q
}

export interface ListShipmentsParams {
  search?: string
  /** 在全部内部/承运商轨迹节点描述中模糊匹配 */
  trackingSearch?: string
  /** 批量精确查询运单号 / 客户订单号（与 search 二选一） */
  shipmentNos?: string[]
  statusCode?: string
  exceptionCode?: string
  hasException?: boolean
  customer?: string
  vipOnly?: boolean
  carrierCode?: string
  countryCode?: string
  channelCode?: string
  channelNameZh?: string
  channelCategory?: string
  vesselVoyage?: string
  customerNo?: string
  destinationPortCode?: string
  addressKeyword?: string
  timeField?: string
  timeFrom?: string
  timeTo?: string
  etdFrom?: string
  etdTo?: string
  atdFrom?: string
  atdTo?: string
  etaFrom?: string
  etaTo?: string
  ataFrom?: string
  ataTo?: string
  expectedDeliveryFrom?: string
  expectedDeliveryTo?: string
  deliveredFrom?: string
  deliveredTo?: string
  createdFrom?: string
  createdTo?: string
  updatedFrom?: string
  updatedTo?: string
  missingEtd?: boolean
  missingAtd?: boolean
  missingEta?: boolean
  missingAta?: boolean
  missingExpectedDelivery?: boolean
  missingDelivered?: boolean
  notDelivered?: boolean
  hasAta?: boolean
  deliveryRisk?: string
  internalFreshness?: TrackingFreshnessBucket
  carrierFreshness?: TrackingFreshnessBucket
  carrierAheadOfInternal?: boolean
  pendingTrackingTimeReview?: boolean
  minStaleDays?: number
  noTracking?: boolean
  noZipcode?: boolean
  groupId?: string
  groupNo?: string
  ruleType?: string
  hasRule?: boolean
  hasGroup?: boolean
  sortBy?: 'shipmentNo'
  sortOrder?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export async function listShipments(params: ListShipmentsParams): Promise<ShipmentListResponse> {
  return api<ShipmentListResponse>('/api/v1/shipments', { query: buildShipmentListQuery(params) })
}

export async function getShipmentFilterOptions(): Promise<ShipmentFilterOptions> {
  return api<ShipmentFilterOptions>('/api/v1/shipments/filter-options')
}

export async function getTrackingFreshnessStats(): Promise<TrackingFreshnessStats> {
  return api<TrackingFreshnessStats>('/api/v1/shipments/tracking-freshness-stats')
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

export async function batchDeleteShipments(ids: string[]): Promise<ShipmentBatchResult> {
  return api<ShipmentBatchResult>('/api/v1/shipments/batch-delete', {
    method: 'POST',
    body: { ids },
  })
}

export async function batchUpdateShipments(
  ids: string[],
  updates: Partial<Omit<ShipmentPayload, 'shipmentNo'>>,
): Promise<ShipmentBatchResult> {
  return api<ShipmentBatchResult>('/api/v1/shipments/batch-update', {
    method: 'PATCH',
    body: { ids, updates },
  })
}

export async function openShipmentExceptions(
  shipmentNos: string[],
  exceptionCode: string,
  options?: { note?: string; openedTime?: string },
): Promise<ShipmentExceptionBatchResult> {
  return api<ShipmentExceptionBatchResult>('/api/v1/shipments/exceptions/open', {
    method: 'POST',
    body: {
      shipmentNos,
      exceptionCode,
      note: options?.note,
      openedTime: options?.openedTime,
    },
  })
}

export async function closeShipmentExceptions(
  shipmentNos: string[],
  options?: { note?: string; closedTime?: string },
): Promise<ShipmentExceptionBatchResult> {
  return api<ShipmentExceptionBatchResult>('/api/v1/shipments/exceptions/close', {
    method: 'POST',
    body: {
      shipmentNos,
      note: options?.note,
      closedTime: options?.closedTime,
    },
  })
}

export async function getShipmentExceptionEvents(
  shipmentId: string,
  params?: { limit?: number; offset?: number },
): Promise<{ items: ShipmentExceptionEvent[]; total: number; limit: number; offset: number }> {
  return api(`/api/v1/shipments/${shipmentId}/exception-events`, { query: params })
}

const SHIPMENT_EXPORT_MAX = 10_000

export async function exportShipmentsExcel(params: ListShipmentsParams): Promise<Blob> {
  const q = buildShipmentListQuery({
    ...params,
    limit: Math.min(params.limit ?? SHIPMENT_EXPORT_MAX, SHIPMENT_EXPORT_MAX),
    offset: 0,
  })
  return api<Blob>('/api/v1/shipments/export', {
    query: q,
    responseType: 'blob',
  })
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

/** 同步承运商轨迹（全库仅转运中；指定单号可含已签收） */
export async function syncCarrierTracking(shipmentNos?: string[]): Promise<TrackingSyncResult> {
  const body = shipmentNos?.length ? { shipmentNos } : undefined
  return api<TrackingSyncResult>('/api/v1/shipments/sync-carrier-tracking', {
    method: 'POST',
    body,
    timeout: 600_000,
  })
}

/** 从 DPS shipment_queryByOrder 按运单号更新选中运单 */
export async function syncShipmentsFromDps(
  shipmentNos: string[],
): Promise<ShipmentDpsSyncByOrderResult> {
  return api<ShipmentDpsSyncByOrderResult>('/api/v1/shipments/sync-from-dps', {
    method: 'POST',
    body: { shipmentNos },
    timeout: 600_000,
  })
}

/** @deprecated 使用 syncTracking() */
export async function syncAllTracking(): Promise<TrackingSyncResult> {
  return syncTracking()
}

export interface ShipmentSubscribeBatchResult {
  total: number
  subscribed: number
  failed: number
  errors: Array<{ shipmentId: string; message: string }>
}

export interface ShipmentUnsubscribeBatchResult {
  total: number
  unsubscribed: number
}

export async function subscribeShipment(shipmentId: string): Promise<{ subscribed: boolean }> {
  return api(`/api/v1/shipments/${encodeURIComponent(shipmentId)}/subscribe`, {
    method: 'POST',
  })
}

export async function unsubscribeShipment(shipmentId: string): Promise<{ subscribed: boolean }> {
  return api(`/api/v1/shipments/${encodeURIComponent(shipmentId)}/subscribe`, {
    method: 'DELETE',
  })
}

export async function batchSubscribeShipments(
  ids: string[],
): Promise<ShipmentSubscribeBatchResult> {
  return api<ShipmentSubscribeBatchResult>('/api/v1/shipments/batch-subscribe', {
    method: 'POST',
    body: { ids },
  })
}

export async function batchUnsubscribeShipments(
  ids: string[],
): Promise<ShipmentUnsubscribeBatchResult> {
  return api<ShipmentUnsubscribeBatchResult>('/api/v1/shipments/batch-unsubscribe', {
    method: 'POST',
    body: { ids },
  })
}

export async function getShipmentTrackingTimeCandidates(
  shipmentId: string,
): Promise<{ items: TrackingTimeCandidate[] }> {
  return api(`/api/v1/shipments/${encodeURIComponent(shipmentId)}/tracking-time-candidates`)
}

export async function recalculateShipmentTrackingTimes(
  shipmentId: string,
): Promise<TrackingTimeRecalculateResult> {
  return api(`/api/v1/shipments/${encodeURIComponent(shipmentId)}/recalculate-tracking-times`, {
    method: 'POST',
  })
}

export async function listPendingTrackingTimeReviews(
  params?: { limit?: number; offset?: number; carrierCode?: string },
): Promise<{
  items: TrackingTimeCandidate[]
  total: number
  limit: number
  offset: number
}> {
  const q: Record<string, string> = {}
  if (params?.limit != null) q.limit = String(params.limit)
  if (params?.offset != null) q.offset = String(params.offset)
  if (params?.carrierCode?.trim()) q.carrierCode = params.carrierCode.trim()
  return api('/api/v1/shipment-tracking-time-candidates/pending', { query: q })
}

export async function reviewTrackingTimeCandidate(
  candidateId: string,
  body: {
    action: import('@/types/trackingTimeWriteback').TrackingTimeReviewAction
    manualValue?: string
  },
): Promise<{ action: string; deliveredTime?: string }> {
  return api(`/api/v1/shipment-tracking-time-candidates/${encodeURIComponent(candidateId)}/review`, {
    method: 'POST',
    body,
  })
}
