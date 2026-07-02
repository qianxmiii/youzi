import { api } from '@/api/client'

export interface DistributionItem {
  key: string
  label: string
  count: number
  ratio: number
}

export interface TransitBaselineStats {
  available: boolean
  sampleCount: number
  avgDays: number | null
  stdDevDays: number | null
  minDays: number | null
  maxDays: number | null
  description: string
}

export interface ShipmentStatisticsOverview {
  total: number
  statusDistribution: DistributionItem[]
  channelDistribution: DistributionItem[]
  seaChannelDistribution: DistributionItem[]
  seaChannelTotal: number
  carrierDistribution: DistributionItem[]
  transitBaseline: TransitBaselineStats
}

export async function getShipmentStatisticsOverview(): Promise<ShipmentStatisticsOverview> {
  return api<ShipmentStatisticsOverview>('/api/v1/statistics/shipments/overview')
}

export interface PerformanceMetricBlock {
  avgDays: number | null
  sampleCount: number
  p50Days: number | null
  p90Days: number | null
  minDays: number | null
  maxDays: number | null
}

export interface PerformanceGroupRow {
  key: string
  label: string
  totalCount: number
  signedCount: number
  signedRate: number
  seaTransit: PerformanceMetricBlock
  postArrival: PerformanceMetricBlock
  fullTransit: PerformanceMetricBlock
  deliveryDeviation: PerformanceMetricBlock
  anomalyCount: number
  anomalyRate: number
  fastestShipmentNo: string | null
  slowestShipmentNo: string | null
}

export interface PerformanceCarrierChannelRow {
  carrierCode: string
  channelCode: string
  totalCount: number
  signedCount: number
  seaTransit: PerformanceMetricBlock
  fullTransit: PerformanceMetricBlock
  anomalyCount: number
  anomalyRate: number
}

export interface ShipmentPerformanceDetailRow {
  shipmentId: string
  shipmentNo: string
  customer: string | null
  channelCode: string | null
  carrierCode: string | null
  destinationPortCode: string | null
  etd: string | null
  atd: string | null
  eta: string | null
  ata: string | null
  expectedDeliveryTime: string | null
  signedTime: string | null
  departureDeviationDays: number | null
  etaDeviationDays: number | null
  seaTransitDays: number | null
  postArrivalDays: number | null
  fullTransitDays: number | null
  deliveryDeviationDays: number | null
  anomalyFlags: string[]
}

export type PerformanceDateBasis = 'atd' | 'ata' | 'signed_time' | 'created_time'

export interface ShipmentPerformanceQueryParams {
  dateFrom?: string
  dateTo?: string
  dateBasis?: PerformanceDateBasis
  channelCode?: string
  carrierCode?: string
  customer?: string
  destinationPortCode?: string
}

export interface ShipmentPerformanceAnalysis {
  filters: ShipmentPerformanceQueryParams & { dateBasis: PerformanceDateBasis }
  truncated: boolean
  analyzedCount: number
  overview: {
    totalCount: number
    signedCount: number
    signedRate: number
    anomalyCount: number
    anomalyRate: number
    seaTransit: PerformanceMetricBlock
    postArrival: PerformanceMetricBlock
    fullTransit: PerformanceMetricBlock
    deliveryDeviation: PerformanceMetricBlock
    fastestSignedTransitDays: number | null
    fastestSignedShipmentNo: string | null
    slowestSignedTransitDays: number | null
    slowestSignedShipmentNo: string | null
    channelRanking: PerformanceGroupRow[]
    carrierRanking: PerformanceGroupRow[]
  }
  byChannel: PerformanceGroupRow[]
  byCarrier: PerformanceGroupRow[]
  byCarrierChannel: PerformanceCarrierChannelRow[]
  byCustomer: PerformanceGroupRow[]
}

export interface ShipmentPerformanceDetailsResponse {
  items: ShipmentPerformanceDetailRow[]
  total: number
  page: number
  pageSize: number
  truncated: boolean
}

function buildPerformanceQuery(params: ShipmentPerformanceQueryParams): Record<string, string> {
  const q: Record<string, string> = {}
  if (params.dateFrom?.trim()) q.dateFrom = params.dateFrom.trim()
  if (params.dateTo?.trim()) q.dateTo = params.dateTo.trim()
  if (params.dateBasis) q.dateBasis = params.dateBasis
  if (params.channelCode?.trim()) q.channelCode = params.channelCode.trim()
  if (params.carrierCode?.trim()) q.carrierCode = params.carrierCode.trim()
  if (params.customer?.trim()) q.customer = params.customer.trim()
  if (params.destinationPortCode?.trim()) q.destinationPortCode = params.destinationPortCode.trim()
  return q
}

export async function getShipmentPerformanceAnalysis(
  params: ShipmentPerformanceQueryParams = {},
): Promise<ShipmentPerformanceAnalysis> {
  return api<ShipmentPerformanceAnalysis>('/api/v1/statistics/shipment-performance', {
    query: buildPerformanceQuery(params),
  })
}

export async function getShipmentPerformanceDetails(
  params: ShipmentPerformanceQueryParams & {
    page?: number
    pageSize?: number
    sortBy?: string
    sortOrder?: 'asc' | 'desc'
  } = {},
): Promise<ShipmentPerformanceDetailsResponse> {
  const q = buildPerformanceQuery(params)
  if (params.page != null) q.page = String(params.page)
  if (params.pageSize != null) q.pageSize = String(params.pageSize)
  if (params.sortBy) q.sortBy = params.sortBy
  if (params.sortOrder) q.sortOrder = params.sortOrder
  return api<ShipmentPerformanceDetailsResponse>('/api/v1/statistics/shipment-performance/details', {
    query: q,
  })
}

export async function exportShipmentPerformanceCsv(
  params: ShipmentPerformanceQueryParams = {},
): Promise<Blob> {
  return api<Blob>('/api/v1/statistics/shipment-performance/export', {
    query: buildPerformanceQuery(params),
    responseType: 'blob',
  })
}

export function formatPerformanceRate(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`
}

export function formatPerformanceMetric(
  block: PerformanceMetricBlock,
  analyzedCount?: number,
): string {
  if (block.avgDays == null || block.sampleCount <= 0) return '—'
  const sample =
    analyzedCount != null && analyzedCount > 0
      ? `${block.sampleCount}/${analyzedCount}`
      : String(block.sampleCount)
  return `${block.avgDays} 天 (${sample})`
}

export function formatPerformanceDays(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${value} 天`
}
