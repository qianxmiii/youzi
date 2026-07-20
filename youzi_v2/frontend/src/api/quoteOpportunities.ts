import { api } from '@/api/client'

export type QuoteScope =
  | 'todo'
  | 'today'
  | 'overdue_followup'
  | 'expiring_soon'
  | 'expired'
  | 'all_active'
  | 'won'
  | 'lost'
  | 'cancelled'

export interface QuoteOpportunity {
  id: string
  quoteNo: string
  customerId: string
  customerName: string
  isNewCustomer: boolean
  customerInquiryNo: string
  quoteDate: string
  deadlineDate: string
  followupIntervalDays: number
  nextFollowupDate: string
  status: string
  displayStatus: string
  statusLabel: string
  owner: string
  productName: string
  addressText: string
  ctns: number | null
  weightKg: number | null
  volumeCbm: number | null
  currentQuoteVersionId: string
  currentQuotedAmount: number | null
  currentQuotedCurrency: string
  currentProfitAmount: number | null
  currentProfitCurrency: string
  currentProfitRate: number | null
  lostReason: string
  note: string
  followupCount: number
  lastFollowupTime: string | null
  lastFollowupNote: string
  createdTime: string
  updatedTime: string
}

export interface QuoteVersion {
  id: string
  quoteId: string
  versionNo: number
  versionTime: string
  changeReason: string
  productName: string
  addressText: string
  ctns: number | null
  weightKg: number | null
  volumeCbm: number | null
  quotedAmount: number | null
  quotedCurrency: string
  profitAmount: number | null
  profitCurrency: string
  profitRate: number | null
  note: string
  createdTime: string
  updatedTime: string
}

export interface QuoteFollowup {
  id: string
  quoteId: string
  quoteVersionId: string
  followupTime: string
  followupType: string
  note: string
  nextFollowupDate: string
  createdBy: string
  createdTime: string
  updatedTime: string
}

export interface QuoteNotificationSummary {
  todayCount: number
  overdueCount: number
  expiringSoonCount: number
  pendingCount: number
}

export type QuoteCreateBody = {
  customerId?: string
  customerName: string
  isNewCustomer?: boolean
  customerInquiryNo?: string
  quoteDate?: string | null
  deadlineDate?: string | null
  followupIntervalDays?: number
  nextFollowupDate?: string | null
  owner?: string
  productName?: string
  addressText?: string
  ctns?: number | null
  weightKg?: number | null
  volumeCbm?: number | null
  quotedAmount?: number | null
  quotedCurrency?: string
  profitAmount?: number | null
  profitCurrency?: string
  profitRate?: number | null
  note?: string
}

export type QuoteFollowupBody = {
  followupType?: string
  note?: string
  nextFollowupDate?: string | null
  adjustQuote?: boolean
  version?: {
    changeReason?: string
    productName?: string
    addressText?: string
    ctns?: number | null
    weightKg?: number | null
    volumeCbm?: number | null
    quotedAmount?: number | null
    quotedCurrency?: string
    profitAmount?: number | null
    profitCurrency?: string
    profitRate?: number | null
    note?: string
  }
}

export async function listQuoteOpportunities(params?: {
  scope?: QuoteScope
  status?: string
  customer?: string
  isNewCustomer?: boolean
  owner?: string
  quoteDateFrom?: string
  quoteDateTo?: string
  deadlineFrom?: string
  deadlineTo?: string
  search?: string
  limit?: number
  offset?: number
}): Promise<{ items: QuoteOpportunity[]; total: number; limit: number; offset: number }> {
  const q: Record<string, string> = {}
  if (params?.scope) q.scope = params.scope
  if (params?.status?.trim()) q.status = params.status.trim()
  if (params?.customer?.trim()) q.customer = params.customer.trim()
  if (params?.isNewCustomer === true) q.isNewCustomer = 'true'
  if (params?.isNewCustomer === false) q.isNewCustomer = 'false'
  if (params?.owner?.trim()) q.owner = params.owner.trim()
  if (params?.quoteDateFrom?.trim()) q.quoteDateFrom = params.quoteDateFrom.trim()
  if (params?.quoteDateTo?.trim()) q.quoteDateTo = params.quoteDateTo.trim()
  if (params?.deadlineFrom?.trim()) q.deadlineFrom = params.deadlineFrom.trim()
  if (params?.deadlineTo?.trim()) q.deadlineTo = params.deadlineTo.trim()
  if (params?.search?.trim()) q.search = params.search.trim()
  if (params?.limit != null) q.limit = String(params.limit)
  if (params?.offset != null) q.offset = String(params.offset)
  return api('/api/v1/quote-opportunities', { query: q })
}

export async function getQuoteNotificationSummary(): Promise<QuoteNotificationSummary> {
  return api('/api/v1/quote-opportunities/notifications/summary')
}

export async function createQuoteOpportunity(body: QuoteCreateBody): Promise<QuoteOpportunity> {
  return api('/api/v1/quote-opportunities', { method: 'POST', body })
}

export async function getQuoteOpportunity(id: string): Promise<QuoteOpportunity> {
  return api(`/api/v1/quote-opportunities/${encodeURIComponent(id)}`)
}

export async function createQuoteFollowup(
  id: string,
  body: QuoteFollowupBody,
): Promise<QuoteFollowup> {
  return api(`/api/v1/quote-opportunities/${encodeURIComponent(id)}/followups`, {
    method: 'POST',
    body,
  })
}

export async function listQuoteVersions(id: string): Promise<{ items: QuoteVersion[] }> {
  return api(`/api/v1/quote-opportunities/${encodeURIComponent(id)}/versions`)
}

export async function listQuoteFollowups(id: string): Promise<{ items: QuoteFollowup[] }> {
  return api(`/api/v1/quote-opportunities/${encodeURIComponent(id)}/followups`)
}

export async function markQuoteWon(id: string): Promise<QuoteOpportunity> {
  return api(`/api/v1/quote-opportunities/${encodeURIComponent(id)}/mark-won`, {
    method: 'POST',
  })
}

export async function markQuoteLost(
  id: string,
  body: { lostReason?: string; note?: string },
): Promise<QuoteOpportunity> {
  return api(`/api/v1/quote-opportunities/${encodeURIComponent(id)}/mark-lost`, {
    method: 'POST',
    body,
  })
}

export async function cancelQuote(id: string): Promise<QuoteOpportunity> {
  return api(`/api/v1/quote-opportunities/${encodeURIComponent(id)}/cancel`, {
    method: 'POST',
  })
}

export async function extendQuoteDeadline(
  id: string,
  body: { deadlineDate: string; nextFollowupDate?: string | null },
): Promise<QuoteOpportunity> {
  return api(`/api/v1/quote-opportunities/${encodeURIComponent(id)}/extend-deadline`, {
    method: 'POST',
    body,
  })
}
