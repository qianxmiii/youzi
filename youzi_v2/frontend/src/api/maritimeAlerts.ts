import { api } from '@/api/client'
import type { MaritimeStatus } from '@/types/vesselSchedule'

export interface MaritimeAlertCounts {
  arrivingSoon: number
  departingSoon: number
  arrived: number
  inTransit: number
  planned: number
  unknown: number
  portArrivingSoon: number
  portDepartingSoon: number
}

export interface MaritimeAlertShipment {
  shipmentNo: string
  customer: string | null
  vesselVoyage: string | null
  maritimeStatus: MaritimeStatus
  maritimeStatusLabel: string
  eta: string | null
  etd: string | null
  destinationPortCode: string | null
}

export interface MaritimeAlertPortCall {
  voyageId: string
  vesselVoyage: string
  portName: string
  sequence: number
  status: MaritimeStatus
  statusLabel: string
  eta: string | null
  etd: string | null
}

export interface VoyageAlertBrief {
  voyageId: string
  vesselVoyage: string
  arrivingSoonPorts: number
  departingSoonPorts: number
}

export interface UnconfiguredVesselVoyage {
  vesselVoyage: string
  shipmentCount: number
}

export interface MaritimeAlertsOverview {
  generatedAt: string
  counts: MaritimeAlertCounts
  urgentShipments: MaritimeAlertShipment[]
  urgentPortCalls: MaritimeAlertPortCall[]
  voyagesWithAlerts: VoyageAlertBrief[]
  unconfiguredVesselVoyages: UnconfiguredVesselVoyage[]
  totalScanned: number
}

export async function getMaritimeAlertsOverview(): Promise<MaritimeAlertsOverview> {
  return api<MaritimeAlertsOverview>('/api/v1/maritime-alerts/overview')
}
