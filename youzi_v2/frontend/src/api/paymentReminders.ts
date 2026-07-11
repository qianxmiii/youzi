import { api } from '@/api/client'

export type PaymentReminderScope =
  | 'todo'
  | 'all_unpaid'
  | 'upcoming_7_days'
  | 'today'
  | 'overdue'
  | 'missing_rule'
  | 'missing_date'

export interface PaymentReminderItem {
  shipmentId: string
  shipmentNo: string
  customer: string
  customerNo: string
  channelCode: string
  channelNameZh: string
  statusCode: string
  latestTrackingTime: string | null
  latestTrackingDesc: string
  paymentStatus: string
  settlementMethod: string | null
  settlementMethodLabel: string
  baseDateField: string
  baseDate: string
  dueDate: string
  reminderDate: string
  reminderType: string
  reminderTypeLabel: string
  daysUntilDue: number
  overdueDays: number
  followupCount: number
  lastFollowupTime: string | null
  lastFollowupNote: string
}

export interface PaymentReminderListResponse {
  items: PaymentReminderItem[]
  total: number
  limit: number
  offset: number
}

export interface PaymentReminderFollowup {
  id: string
  shipmentId: string
  shipmentNo: string
  customer: string
  settlementMethod: string
  reminderType: string
  dueDate: string
  followupTime: string
  note: string
  createdBy: string
  createdTime: string
  updatedTime: string
}

export interface PaymentReminderFollowupBatchResult {
  total: number
  created: number
  failed: number
  errors: { id?: string; message?: string }[]
}

export async function listPaymentReminders(params?: {
  scope?: PaymentReminderScope
  customer?: string
  settlementMethod?: string
  reminderType?: string
  search?: string
  limit?: number
  offset?: number
}): Promise<PaymentReminderListResponse> {
  const q: Record<string, string> = {}
  if (params?.scope) q.scope = params.scope
  if (params?.customer?.trim()) q.customer = params.customer.trim()
  if (params?.settlementMethod?.trim()) q.settlementMethod = params.settlementMethod.trim()
  if (params?.reminderType?.trim()) q.reminderType = params.reminderType.trim()
  if (params?.search?.trim()) q.search = params.search.trim()
  if (params?.limit != null) q.limit = String(params.limit)
  if (params?.offset != null) q.offset = String(params.offset)
  return api<PaymentReminderListResponse>('/api/v1/shipments/payment-reminders', { query: q })
}

export async function listPaymentReminderFollowups(
  shipmentId: string,
): Promise<{ items: PaymentReminderFollowup[] }> {
  return api(`/api/v1/shipments/payment-reminders/${shipmentId}/followups`)
}

export async function createPaymentReminderFollowup(
  shipmentId: string,
  note: string,
): Promise<PaymentReminderFollowup> {
  return api(`/api/v1/shipments/payment-reminders/${shipmentId}/followups`, {
    method: 'POST',
    body: { note },
  })
}

export async function batchCreatePaymentReminderFollowups(
  shipmentIds: string[],
  note: string,
): Promise<PaymentReminderFollowupBatchResult> {
  return api('/api/v1/shipments/payment-reminders/followups/batch', {
    method: 'POST',
    body: { shipmentIds, note },
  })
}
