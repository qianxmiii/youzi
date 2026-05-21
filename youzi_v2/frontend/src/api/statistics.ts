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
