import { api } from '@/api/client'

export type CustomerLang = 'zh' | 'en'

export interface Customer {
  id: string
  customerName: string
  customerLang: CustomerLang
  isVip: boolean
  note: string
  shipmentCount: number
  settlementMethod?: string | null
  settlementDay?: number | null
  createdTime: string
  updatedTime: string
}

export interface CustomerListResponse {
  items: Customer[]
  total: number
  limit: number
  offset: number
}

export interface CustomerSyncResult {
  added: number
  total: number
  fromShipments: number
}

export type CustomerPatch = {
  customerName?: string
  updateShipments?: boolean
  isVip?: boolean
  note?: string
  customerLang?: CustomerLang
  settlementMethod?: string | null
  settlementDay?: number | null
}

export type CustomerUpdateResult = Customer & {
  shipmentsUpdated?: number
}

export async function listCustomers(params?: {
  search?: string
  vipOnly?: boolean
  limit?: number
  offset?: number
}): Promise<CustomerListResponse> {
  const q: Record<string, string> = {}
  if (params?.search?.trim()) q.search = params.search.trim()
  if (params?.vipOnly === true) q.vipOnly = 'true'
  if (params?.vipOnly === false) q.vipOnly = 'false'
  if (params?.limit != null) q.limit = String(params.limit)
  if (params?.offset != null) q.offset = String(params.offset)
  return api<CustomerListResponse>('/api/v1/customers', { query: q })
}

export async function syncCustomersFromShipments(): Promise<CustomerSyncResult> {
  return api<CustomerSyncResult>('/api/v1/customers/sync-from-shipments', {
    method: 'POST',
  })
}

export async function createCustomer(
  customerName: string,
  options?: {
    note?: string
    isVip?: boolean
    customerLang?: CustomerLang
  },
): Promise<Customer> {
  return api<Customer>('/api/v1/customers', {
    method: 'POST',
    body: {
      customerName: customerName.trim(),
      note: options?.note?.trim() || '',
      isVip: options?.isVip ?? false,
      customerLang: options?.customerLang ?? 'zh',
    },
  })
}

export async function updateCustomer(
  id: string,
  patch: CustomerPatch,
): Promise<CustomerUpdateResult> {
  return api<CustomerUpdateResult>(`/api/v1/customers/${id}`, {
    method: 'PATCH',
    body: patch,
  })
}

export async function deleteCustomer(id: string): Promise<void> {
  await api(`/api/v1/customers/${id}`, { method: 'DELETE' })
}

