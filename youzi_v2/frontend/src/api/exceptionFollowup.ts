import { api } from '@/api/client'

export interface ShipmentExceptionFollowupNotification {
  id: string
  shipmentId: string
  shipmentNo: string
  exceptionCode: string
  exceptionNameZh?: string | null
  severity: string
  title: string
  message: string
  daysOpen: number
  followupIntervalDays: number
  eventKey: string
  triggeredAt: string
  readAt?: string | null
  resolvedAt?: string | null
  customer?: string | null
}

export async function getExceptionFollowupTodoNotifications(limit = 20): Promise<{
  items: ShipmentExceptionFollowupNotification[]
  pendingCount: number
}> {
  return api(`/api/v1/shipment-exception-followups/notifications`, {
    query: { limit: String(limit), scope: 'todo' },
  })
}

export async function markExceptionFollowupNotificationRead(id: string): Promise<void> {
  await api(`/api/v1/shipment-exception-followups/notifications/${encodeURIComponent(id)}/read`, {
    method: 'POST',
  })
}

export async function resolveExceptionFollowupNotification(id: string): Promise<void> {
  await api(
    `/api/v1/shipment-exception-followups/notifications/${encodeURIComponent(id)}/resolve`,
    { method: 'POST' },
  )
}
