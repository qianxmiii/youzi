import { api } from '@/api/client'

export type CustomerAddressKind = 'WAREHOUSE' | 'COMMERCIAL' | 'RESIDENTIAL'

export interface CustomerAddress {
  id: string
  customerName: string
  label: string
  consigneeName: string
  company: string
  phone: string
  email: string
  country: string
  address: string
  postcode: string
  addressKind: CustomerAddressKind | string
  isRemote: boolean
  note: string
  createdTime: string
  updatedTime: string
}

export interface CustomerAddressPayload {
  customerName: string
  label?: string
  consigneeName?: string
  company?: string
  phone?: string
  email?: string
  country: string
  address: string
  postcode?: string
  addressKind: string
  isRemote?: boolean
  note?: string
}

export interface CustomerAddressListResponse {
  items: CustomerAddress[]
  total: number
  limit: number
  offset: number
}

export interface CustomerAddressImportResult {
  created: number
  failed: number
  errors: Array<{ row: number; message: string }>
}

export interface CustomerAddressQuery {
  customer?: string
  addressKind?: string
  remote?: boolean
  search?: string
  limit?: number
  offset?: number
}

function queryOf(params?: CustomerAddressQuery): Record<string, string> {
  const q: Record<string, string> = {}
  if (params?.customer?.trim()) q.customer = params.customer.trim()
  if (params?.addressKind?.trim()) q.addressKind = params.addressKind.trim()
  if (params?.remote === true) q.remote = 'true'
  if (params?.remote === false) q.remote = 'false'
  if (params?.search?.trim()) q.search = params.search.trim()
  if (params?.limit != null) q.limit = String(params.limit)
  if (params?.offset != null) q.offset = String(params.offset)
  return q
}

export async function listCustomerAddresses(
  params?: CustomerAddressQuery,
): Promise<CustomerAddressListResponse> {
  return api<CustomerAddressListResponse>('/api/v1/customer-addresses', {
    query: queryOf(params),
  })
}

export async function createCustomerAddress(
  payload: CustomerAddressPayload,
): Promise<CustomerAddress> {
  return api<CustomerAddress>('/api/v1/customer-addresses', {
    method: 'POST',
    body: payload,
  })
}

export async function updateCustomerAddress(
  id: string,
  payload: CustomerAddressPayload,
): Promise<CustomerAddress> {
  return api<CustomerAddress>(`/api/v1/customer-addresses/${id}`, {
    method: 'PUT',
    body: payload,
  })
}

export async function deleteCustomerAddress(id: string): Promise<{ deleted: boolean }> {
  return api(`/api/v1/customer-addresses/${id}`, { method: 'DELETE' })
}

export async function batchDeleteCustomerAddresses(
  ids: string[],
): Promise<{ deleted: number }> {
  return api('/api/v1/customer-addresses/batch-delete', {
    method: 'POST',
    body: { ids },
  })
}

export async function exportCustomerAddressesExcel(
  params?: CustomerAddressQuery,
): Promise<Blob> {
  return api<Blob, 'blob'>('/api/v1/customer-addresses/export', {
    query: queryOf(params),
    responseType: 'blob',
  })
}

export async function downloadCustomerAddressTemplate(): Promise<Blob> {
  return api<Blob, 'blob'>('/api/v1/customer-addresses/template', {
    responseType: 'blob',
  })
}

export async function importCustomerAddressesExcel(
  file: File,
): Promise<CustomerAddressImportResult> {
  const form = new FormData()
  form.append('file', file)
  return api<CustomerAddressImportResult>('/api/v1/customer-addresses/import', {
    method: 'POST',
    body: form,
  })
}
