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
  refShipmentNo?: string
  billOfLadingNo?: string
  containerNo?: string
  isFcl?: boolean
  channelCode: string
  channelNameZh: string
  statusCode: string
  ata?: string | null
  deliveredTime?: string | null
  latestTrackingTime: string | null
  latestTrackingDesc: string
  paymentStatus: string
  /** 应收，人民币 */
  receivableCny?: number | null
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

export interface PaymentReminderCustomerRank {
  customer: string
  total: number
  overdue: number
  open: number
  count: number
}

export interface PaymentReminderCustomerRanking {
  items: PaymentReminderCustomerRank[]
  pendingCount: number
  totalReceivable: number
}

export interface PaymentReminderSummary {
  todoCount: number
  allUnpaidCount: number
  overdueCount: number
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

export type PaymentReminderListParams = {
  scope?: PaymentReminderScope
  customer?: string
  settlementMethod?: string
  reminderType?: string
  followupStatus?: 'unfollowed' | 'followed'
  search?: string
  /** true=仅整柜；false=排除整柜；与运单列表一致，前端默认 false */
  fclOnly?: boolean
  /** 只保留应收大于等于该金额的票；空应收不计入 */
  minReceivable?: number
  /** 只保留未记应收或应收小于等于 0 的票 */
  receivablePending?: boolean
  /** receivable：按应收从高到低，空应收仍在最后 */
  sortBy?: 'receivable'
  channelCategory?: string
  limit?: number
  offset?: number
}

function buildReminderQuery(params?: PaymentReminderListParams): Record<string, string> {
  const q: Record<string, string> = {}
  if (params?.scope) q.scope = params.scope
  if (params?.customer?.trim()) q.customer = params.customer.trim()
  if (params?.settlementMethod?.trim()) q.settlementMethod = params.settlementMethod.trim()
  if (params?.reminderType?.trim()) q.reminderType = params.reminderType.trim()
  if (params?.followupStatus) q.followupStatus = params.followupStatus
  if (params?.search?.trim()) q.search = params.search.trim()
  if (params?.fclOnly === true) q.fclOnly = 'true'
  if (params?.fclOnly === false) q.fclOnly = 'false'
  if (params?.minReceivable != null) q.minReceivable = String(params.minReceivable)
  if (params?.receivablePending) q.receivablePending = 'true'
  if (params?.sortBy) q.sortBy = params.sortBy
  if (params?.channelCategory?.trim()) q.channelCategory = params.channelCategory.trim()
  if (params?.limit != null) q.limit = String(params.limit)
  if (params?.offset != null) q.offset = String(params.offset)
  return q
}

export async function listPaymentReminders(
  params?: PaymentReminderListParams,
): Promise<PaymentReminderListResponse> {
  return api<PaymentReminderListResponse>('/api/v1/shipments/payment-reminders', {
    query: buildReminderQuery(params),
  })
}

export async function getPaymentReminderCustomerRanking(
  params?: PaymentReminderListParams,
): Promise<PaymentReminderCustomerRanking> {
  return api<PaymentReminderCustomerRanking>('/api/v1/shipments/payment-reminders/customer-ranking', {
    query: buildReminderQuery(params),
  })
}

export async function getPaymentReminderSummary(params?: {
  fclOnly?: boolean
}): Promise<PaymentReminderSummary> {
  return api<PaymentReminderSummary>('/api/v1/shipments/payment-reminders/summary', {
    query: buildReminderQuery({ fclOnly: params?.fclOnly }),
  })
}

const REMINDER_EXPORT_MAX = 10_000

export async function exportPaymentRemindersExcel(
  params?: PaymentReminderListParams,
): Promise<Blob> {
  return api<Blob, 'blob'>('/api/v1/shipments/payment-reminders/export', {
    query: buildReminderQuery({
      ...params,
      limit: Math.min(params?.limit ?? REMINDER_EXPORT_MAX, REMINDER_EXPORT_MAX),
      offset: 0,
    }),
    responseType: 'blob',
  })
}

export async function setPaymentCollectionTerm(
  shipmentIds: string[],
  collectionStartDate: string,
  paymentTermDays = 21,
  reminderAdvanceDays = 7,
): Promise<{ updated: number; missing: number }> {
  return api('/api/v1/shipments/payment-reminders/collection-term', {
    method: 'POST',
    body: { shipmentIds, collectionStartDate, paymentTermDays, reminderAdvanceDays },
  })
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
