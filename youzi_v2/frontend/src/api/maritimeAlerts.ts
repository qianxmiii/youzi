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
  /** 挂靠港 ETA 三天内到港（无需订阅） */
  etaArrivingSoonPortCalls: MaritimeAlertPortCall[]
  /** 运单 ETA 三天内到港 */
  etaArrivingSoonShipments: MaritimeAlertShipment[]
  voyagesWithAlerts: VoyageAlertBrief[]
  unconfiguredVesselVoyages: UnconfiguredVesselVoyage[]
  totalScanned: number
  portArrivalNotifications: PortArrivalNotification[]
  shipmentArrivalNotifications: ShipmentArrivalNotification[]
}

export interface PortArrivalNotification {
  id: string
  subscriptionId: string
  portCallId: string
  voyageId: string
  portName: string
  vesselVoyage: string
  ata: string
  createdAt: string
  readAt: string | null
}

export interface ShipmentArrivalNotification {
  id: string
  subscriptionId: string
  shipmentId: string
  shipmentNo: string
  customer: string | null
  vesselVoyage: string
  destinationPortCode: string
  trackingSource: 'internal' | 'carrier' | 'arrival' | string
  latestTime: string
  latestDesc: string
  createdAt: string
  readAt: string | null
}

export async function getMaritimeAlertsOverview(): Promise<MaritimeAlertsOverview> {
  return api<MaritimeAlertsOverview>('/api/v1/maritime-alerts/overview')
}

export async function markPortArrivalNotificationRead(notificationId: string): Promise<void> {
  await api(`/api/v1/maritime-alerts/port-arrivals/${encodeURIComponent(notificationId)}/read`, {
    method: 'POST',
  })
}

export async function markShipmentArrivalNotificationRead(notificationId: string): Promise<void> {
  await api(
    `/api/v1/maritime-alerts/shipment-arrivals/${encodeURIComponent(notificationId)}/read`,
    { method: 'POST' },
  )
}

export interface MarkAllMaritimeNotificationsReadResult {
  port: number
  shipment: number
  total: number
}

export async function markAllMaritimeNotificationsRead(): Promise<MarkAllMaritimeNotificationsReadResult> {
  return api<MarkAllMaritimeNotificationsReadResult>(
    '/api/v1/maritime-alerts/notifications/read-all',
    { method: 'POST' },
  )
}
