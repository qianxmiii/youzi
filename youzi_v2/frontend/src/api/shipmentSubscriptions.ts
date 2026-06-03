import { api } from '@/api/client'

export interface ShipmentTrackingNotification {
  id: string
  subscriptionId: string
  shipmentId: string
  shipmentNo: string
  customer: string | null
  vesselVoyage: string
  destinationPortCode: string
  trackingSource: string
  latestTime: string
  latestDesc: string
  createdAt: string
  readAt: string | null
}

export interface ShipmentTrackingNotificationsResponse {
  items: ShipmentTrackingNotification[]
  unreadCount: number
}

export async function getShipmentTrackingNotifications(
  limit = 20,
): Promise<ShipmentTrackingNotificationsResponse> {
  return api<ShipmentTrackingNotificationsResponse>(
    '/api/v1/shipment-subscriptions/notifications?limit=' + String(limit),
  )
}

export async function markShipmentTrackingNotificationRead(notificationId: string): Promise<void> {
  await api(
    '/api/v1/maritime-alerts/shipment-arrivals/' + encodeURIComponent(notificationId) + '/read',
    { method: 'POST' },
  )
}

export async function markAllShipmentTrackingNotificationsRead(): Promise<{ count: number }> {
  return api<{ count: number }>('/api/v1/shipment-subscriptions/notifications/read-all', {
    method: 'POST',
  })
}
